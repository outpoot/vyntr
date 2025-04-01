import { BLIPTEXT_ENDPOINT, SEARCH_KEY } from '$env/static/private';
import type { SearchResults } from '$lib/types/article';
import { tryCatch } from '$lib/utils/result';

export async function searchBliptext(query: string): Promise<SearchResults> {
    if (!query || query.length < 2) {
        return { scores: [], bestMatch: null };
    }

    const searchUrl = BLIPTEXT_ENDPOINT + '?q=' + encodeURIComponent(query);

    const [response, error] = await tryCatch(fetch(searchUrl, {
        headers: {
            'x-search-key': SEARCH_KEY
        }
    }));

    if (error) {
        console.error('Bliptext search error:', error);
        return { scores: [], bestMatch: null };
    }

    if (!response.ok) {
        console.log(await response.text())
        console.error('Bliptext search failed:', response.statusText);
        return { scores: [], bestMatch: null };
    }

    return await response.json();
}