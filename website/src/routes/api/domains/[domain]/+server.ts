import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { website } from '$lib/server/schema';
import { and, eq } from 'drizzle-orm';
import { auth } from '$lib/auth';
import type { RequestHandler } from './$types';

export const PATCH: RequestHandler = async ({ request, params }) => {
    const session = await auth.api.getSession({
        headers: request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    const domain = `https://${params.domain}`;
    const updates = await request.json();

    // Validate inputs
    if (updates.description?.length > 200) {
        throw error(400, 'Description too long');
    }

    if (updates.tags?.some((tag: string) => tag.length > 34)) {
        throw error(400, 'Tags too long');
    }

    // Update website
    const result = await db.update(website)
        .set({
            ...updates,
            updatedAt: new Date()
        })
        .where(and(
            eq(website.domain, domain),
            eq(website.userId, session.user.id)
        ))
        .returning();

    if (!result.length) {
        throw error(404, 'Domain not found');
    }

    return new Response(JSON.stringify(result[0]));
};
