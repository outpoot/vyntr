import { error, json } from '@sveltejs/kit';

import { auth } from '$lib/auth';
import { db } from '$lib/server/db';
import { userPreferences } from '$lib/server/schema';
import { eq } from 'drizzle-orm';
import { performSearch } from '$lib/server/search';

export async function GET({ url, request }) {
    const query = url.searchParams.get('q');
    if (!query) {
        throw error(400, 'Query parameter "q" is required');
    }

    let userPrefs = null;

    const session = await auth.api.getSession({ headers: request.headers });
    if (session?.user) {
        userPrefs = await db.query.userPreferences.findFirst({
            where: eq(userPreferences.userId, session.user.id)
        });
    }

    const results = await performSearch(query, userPrefs);
    return json(results);
}