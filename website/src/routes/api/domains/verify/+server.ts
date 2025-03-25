import { error } from '@sveltejs/kit';
import { verifyDomainTXT } from '$lib/utils/dns';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request }) => {
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

    return new Response(null, { status: 204 });
};
