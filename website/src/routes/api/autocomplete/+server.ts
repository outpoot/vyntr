import { json } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { searchQueries } from '$lib/server/schema';
import { desc, sql } from 'drizzle-orm';

export async function GET({ url }) {
    const query = url.searchParams.get('q')?.toLowerCase().trim() || '';

    if (query.length < 2) {
        return json([]);
    }

    const escaped = query.replace(/[\\%_]/g, '\\$&');

    const suggestions = await db.select({
        query: searchQueries.query,
        count: searchQueries.count
    })
        .from(searchQueries)
        .where(sql`${searchQueries.query} LIKE ${escaped + '%'} ESCAPE '\\' AND ${searchQueries.count} >= 3`)
        .orderBy(desc(searchQueries.count))
        .limit(10);

    return json(suggestions.map(s => s.query));
}
