import { error } from '@sveltejs/kit';
import { verifyDomainTXT } from '$lib/utils/dns';
import { db } from '$lib/server/db';
import { website } from '$lib/server/schema';
import { auth } from '$lib/auth';
import { PUBLIC_PRODUCT_ID_PREMIUM } from '$env/static/public';
import type { RequestHandler } from './$types';
import { eq } from 'drizzle-orm';
import { checkPremiumStatus } from '$lib/server/authHelper';
import { normalizeHost, verificationTokenFor } from '$lib/server/domainToken';

export const GET: RequestHandler = async ({ request, url }) => {
    const session = await auth.api.getSession({ headers: request.headers });
    if (!session?.user) throw error(401, 'Not authenticated');

    const host = normalizeHost(url.searchParams.get('domain') ?? '');
    if (!host) throw error(400, 'Invalid domain');

    return new Response(JSON.stringify({ token: verificationTokenFor(session.user.id, host) }), {
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
    });
};

export const POST: RequestHandler = async ({ request, fetch }) => {
    const session = await auth.api.getSession({
        headers: request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    // Check subscription status
    const isPremium = await checkPremiumStatus(session.user.id);

    const domains = await db.query.website.findMany({
        where: eq(website.userId, session.user.id)
    });

    const maxDomains = isPremium ? 50 : 20;
    if (domains.length >= maxDomains) {
        throw error(403, isPremium ? 
            "You've reached the maximum limit of 50 domains." :
            "You've reached the free limit of 20 domains. Upgrade to Premium to register up to 50 domains."
        );
    }

    const { domain: rawDomain } = await request.json();

    const host = normalizeHost(rawDomain);
    if (!host) {
        throw error(400, 'Invalid input');
    }
    const domain = `https://${host}`;

    const [verified, dnsError] = await verifyDomainTXT(host, verificationTokenFor(session.user.id, host));

    if (dnsError) {
        throw error(dnsError.status, dnsError.message);
    }

    if (!verified) {
        throw error(404, 'TXT record not found or does not match');
    }

    // Create website entry
    const newWebsite = await db.insert(website).values({
        domain,
        userId: session.user.id,
        verifiedAt: new Date(),
        status: 'unlisted',
        category: 'uncategorized',
        createdAt: new Date(),
        updatedAt: new Date()
    }).returning();

    return new Response(JSON.stringify(newWebsite[0]), {
        status: 201,
        headers: {
            'Content-Type': 'application/json'
        }
    });
};
