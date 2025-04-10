import { json } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { searchQueries } from '$lib/server/schema';
import { desc, like } from 'drizzle-orm';

export async function GET({ url }) {
    const query = url.searchParams.get('q')?.toLowerCase().trim() || '';

    if (query.length < 2) {
        return json([]);
    }

    const suggestions = await db.select({
        query: searchQueries.query,
        count: searchQueries.count
    })
        .from(searchQueries)
        .where(like(searchQueries.query, `${query}%`))
        .orderBy(desc(searchQueries.count))
        .limit(10);

    return json(suggestions.map(s => s.query));
}
