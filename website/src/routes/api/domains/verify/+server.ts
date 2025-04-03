import { error } from '@sveltejs/kit';
import { verifyDomainTXT } from '$lib/utils/dns';
import { db } from '$lib/server/db';
import { website } from '$lib/server/schema';
import { auth } from '$lib/auth';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request }) => {
    const session = await auth.api.getSession({
        headers: request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    const { domain, verificationToken } = await request.json();

    if (!domain || !verificationToken) {
        throw error(400, 'Invalid input');
    }

    const [verified, dnsError] = await verifyDomainTXT(domain, verificationToken);

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
