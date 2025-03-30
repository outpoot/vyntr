import { error, json } from '@sveltejs/kit';
import { searchWordnet } from '$lib/server/wordnet';

export async function GET({ params }: { params: { term: string } }) {
    const searchTerm = params.term;
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
