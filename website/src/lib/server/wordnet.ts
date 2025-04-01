import postgres from 'postgres';
import { DATABASE_URL } from '$env/static/private';
import type { WordDefinitionSearchDetail } from '$lib/types/searchDetails';

const SIMILARITY_THRESHOLD = 1;
const MEANING_THRESHOLD = 0.6;  // Lower threshold for meaning queries
const LIMIT_RESULTS = 10;

if (!DATABASE_URL) {
    throw new Error('PRIVATE_DB_URL environment variable is not set');
}

const sql = postgres(DATABASE_URL);

interface WordMatch {
    similarity: number;
    entry: WordDefinitionSearchDetail;
}

export async function searchWordnet(searchTerm: string): Promise<WordMatch[]> {
    const meaningWords = [
        'meaning',
        'define',
        'definition',
        'means',
        'mean',
        'what is',
        'whats',
        "what's",
        'explain',
        'description',
        'describe'
    ];
    let processedSearchTerm = searchTerm.trim().toLowerCase();

    const isExplicit = meaningWords.some(word => processedSearchTerm.includes(word));
    const threshold = isExplicit ? MEANING_THRESHOLD : SIMILARITY_THRESHOLD;

    if (isExplicit) {
        meaningWords.forEach(word => {
            processedSearchTerm = processedSearchTerm.replace(word, '');
        });
        processedSearchTerm = processedSearchTerm.trim();
    }

    if (!processedSearchTerm) {
        return [];
    }

    const rows = await sql<{ similarity: number; data: any }[]>`
        SELECT
            similarity(lower(word), ${processedSearchTerm}) AS similarity,
            json_build_object(
                'id', id,
                'word', word,
                'partOfSpeech', part_of_speech,
                'pronunciations', pronunciations,
                'definitions', definitions,
                'examples', examples,
                'synonyms', synonyms,
                'similarWords', similar_words
            ) as data
        FROM wordnet
        WHERE
            lower(word) % ${processedSearchTerm}
            AND similarity(lower(word), ${processedSearchTerm}) >= ${threshold}
        ORDER BY
            (lower(word) = ${processedSearchTerm}) DESC,
            similarity DESC
        LIMIT ${LIMIT_RESULTS}
    `;

    return rows.map(row => ({
        similarity: row.similarity,
        entry: { type: 'word', ...row.data }
    }));
}
