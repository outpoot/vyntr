import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { website } from '$lib/server/schema';
import { and, eq } from 'drizzle-orm';
import { auth } from '$lib/auth';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, params }) => {
    const session = await auth.api.getSession({
        headers: request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    const domain = `https://${params.domain}`;

    const result = await db.update(website)
        .set({
            status: 'pending',
            updatedAt: new Date()
        })
        .where(and(
            eq(website.domain, domain),
            eq(website.userId, session.user.id),
            eq(website.isVerified, false),
            eq(website.status, 'unlisted')
        ))
        .returning();

    if (!result.length) {
        throw error(404, 'Domain not found or not eligible for publishing');
    }

    return new Response(JSON.stringify(result[0]));
};