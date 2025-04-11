import { requireAdmin } from '$lib/server/authHelper';
import { db } from '$lib/server/db';
import { website } from '$lib/server/schema';
import { eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
    await requireAdmin(event);

    const domains = await db.query.website.findMany({
        where: eq(website.status, 'pending'),
        with: {
            user: true
        },
        orderBy: website.createdAt,
    });

    return { domains };
};
