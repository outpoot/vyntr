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
    const body = await request.json();

    const updates: { description?: string | null; tags?: string[]; category?: string } = {};
    if (body.description !== undefined) {
        if (body.description !== null && typeof body.description !== 'string') throw error(400, 'Invalid description');
        if (body.description && body.description.length > 200) throw error(400, 'Description too long');
        updates.description = body.description;
    }
    if (body.tags !== undefined) {
        if (!Array.isArray(body.tags) || body.tags.length > 20 || body.tags.some((t: unknown) => typeof t !== 'string')) {
            throw error(400, 'Invalid tags');
        }
        if (body.tags.some((tag: string) => tag.length > 34)) throw error(400, 'Tags too long');
        updates.tags = body.tags;
    }
    if (body.category !== undefined) {
        if (typeof body.category !== 'string' || body.category.length === 0 || body.category.length > 40) {
            throw error(400, 'Invalid category');
        }
        updates.category = body.category;
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
