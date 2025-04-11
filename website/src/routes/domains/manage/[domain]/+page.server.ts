import { error, redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { website } from '$lib/server/schema';
import { and, eq } from 'drizzle-orm';
import { auth } from '$lib/auth';

export async function load({ request, params }) {
    const session = await auth.api.getSession({
        headers: request.headers
    });

    if (!session?.user) {
        throw error(401, 'Unauthorized');
    }

    const domain = await db.query.website.findFirst({
        where: and(
            eq(website.domain, `https://${params.domain}`),
            eq(website.userId, session.user.id)
        )
    });

    if (!domain) {
        throw error(404, 'Domain not found');
    }

    return { domain };
}
