import { error, redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { website } from '$lib/server/schema';
import { eq } from 'drizzle-orm';
import { auth } from '$lib/auth';

export async function load({ request }) {
    const session = await auth.api.getSession({
        headers: request.headers
    });

    if (!session?.user) {
        throw redirect(302, '/login');
    }

    const domains = await db.query.website.findMany({
        where: eq(website.userId, session.user.id),
        orderBy: website.createdAt,
    });

    return { domains };
}