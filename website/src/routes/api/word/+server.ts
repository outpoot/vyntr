import { error, json } from '@sveltejs/kit';
import { searchWordnet } from '$lib/server/wordnet';

export async function GET({ url }: { url: URL }) {
    const searchTerm = url.searchParams.get('term');
    if (!searchTerm) {
        throw error(400, 'Search term is required');
    }

    try {
        const matches = await searchWordnet(searchTerm);
        return json(matches);
    } catch (err) {
        console.error('Database query failed:', err);
        throw error(500, 'Failed to query database');
    }
}
