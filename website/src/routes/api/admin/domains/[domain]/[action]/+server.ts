import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { website } from '$lib/server/schema';
import { eq } from 'drizzle-orm';
import { requireAdmin } from '$lib/server/admin';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async (event) => {
    await requireAdmin(event);
    const { domain, action } = event.params;

    if (!['approve', 'reject'].includes(action)) {
        throw error(400, 'Invalid action');
    }

    const result = await db.update(website)
        .set({
            status: action === 'approve' ? 'public' : 'unlisted',
            updatedAt: new Date()
        })
        .where(eq(website.domain, `https://${domain}`))
        .returning();

    if (!result.length) {
        throw error(404, 'Domain not found');
    }

    return new Response(JSON.stringify(result[0]));
};
