import { sql } from './db';
import type { ArticleData, ArticleSummary, SearchResults, SearchScore } from '$lib/types/article';

// This is a set of keys that should be included in the summary
// This is to prevent the summary from having useless information
const ALLOWED_KEYS = new Set([
    'Name', 'Founded', 'Location', 'Founder', 'Revenue', 'Employees',
    'Programming Language', 'Users', 'Launched', 'Birth Name', 'Birth Date',
    'Occupation', 'Office', 'Term Start', 'Party', 'Nationality', 'Alias',
    'Years Active', 'Works', 'Other Names', 'Recorded', 'Artist', 'Genre'
]);
const FILLER_WORDS = new Set([
    'who', 'is', 'was', 'are', 'were', 'does', 'do', 'did', 'about',
    'the', 'a', 'an', 'of', 'for', 'on', 'in', 'at', 'to', 'by', 'with',
    'what', 'when', 'where', 'why', 'how', 'which', 'whom', 'whose', 'that', 'this',
    'biography', 'profile', 'history', 'info', 'information', 'age', 'net worth',
    'career', 'background', 'meaning', 'explanation', 'summary', 'details',
]);

function sanitizeMarkdown(text: string): string {
    return text
        // headers
        .replace(/^#\s+/, '')
        // bold
        .replace(/\*\*(.*?)\*\*/g, '$1')
        // italic
        .replace(/\*(.*?)\*/g, '$1')
        .replace(/_(.*?)_/g, '$1')
        // Extract text from links
        .replace(/\[(.*?)\]\(.*?\)/g, '$1')
        .trim();
}

function parseSummary(content: string): ArticleSummary {
    const summary_ = content.match(/:::summary\n([\s\S]*?):::/);
    if (!summary_) return { keys: [] };

    const summary = summary_[1];
    const image = summary.match(/!\[(.*?)\]\((.*?)\)/);
    const keyMatches = Array.from(summary.matchAll(/\*\*(.*?):\*\* (.*?)(?=\n|$)/g));

    // first paragraph after summary
    const introduction_ = content.slice(summary_.index! + summary_[0].length).trim();
    const introduction = introduction_.split('\n\n')[0].trim();

    return {
        image: image ? {
            caption: image[1],
            url: image[2].replace(/\/\/\//g, "_")
        } : undefined,
        keys: keyMatches
            .map(match => ({
                key: match[1].trim(),
                value: sanitizeMarkdown(match[2].trim())
            }))
            .filter(k => k.key && k.value && ALLOWED_KEYS.has(k.key)),
        introduction: introduction ? sanitizeMarkdown(introduction) : undefined
    };
}

async function sanitizeQuery(query: string): Promise<string> {
    const searchQuery = query.trim().slice(0, 200);

    if (!searchQuery || searchQuery.length < 2) {
        return '';
    }

    return searchQuery;
}

// this is used in stuff like bliptext lookups
async function excludeFillerWordsFromQuery(query: string): Promise<string> {
    const wordRegex = /\b\w+\b/g;
    const matches = query.match(wordRegex) || [];

    return matches
        .filter(word => !FILLER_WORDS.has(word.toLowerCase()))
        .join(' ');
}

export async function searchBliptext(query: string): Promise<SearchResults> {
    const rawSearchQuery = await sanitizeQuery(query);
    const searchQuery = await excludeFillerWordsFromQuery(rawSearchQuery);

    console.log('Searching with query:', searchQuery);

    const searchResults = await sql<SearchScore[]>`
        WITH ranked_results AS (
            SELECT 
                slug,
                title,
                (
                    ts_rank_cd(search_vector, websearch_to_tsquery('english', ${searchQuery}), 32) * 2 +
                    CASE 
                        WHEN title ILIKE ${searchQuery} THEN 2
                        WHEN title ILIKE ${searchQuery + '%'} THEN 1
                        ELSE 0
                    END -
                    (length(title) * 0.001)
                ) as score
            FROM articles
            WHERE search_vector @@ websearch_to_tsquery('english', ${searchQuery})
        )
        SELECT *
        FROM ranked_results
        WHERE score > 0
        ORDER BY score DESC
        LIMIT 10
    `;

    console.log('Search results:', searchResults);

    if (searchResults.length === 0) {
        return { scores: [], bestMatch: null };
    }

    const bestScore = searchResults[0];
    console.log('Best score:', bestScore);

    let bestMatch: ArticleData | null = null;

    // only fetch full article if score is good enough
    if (bestScore.score >= 0.1) {
        const [article] = await sql<[{ slug: string, title: string, content: string }?]>`
            SELECT slug, title, content
            FROM articles
            WHERE slug = ${bestScore.slug}
        `;

        if (article) {
            bestMatch = {
                ...article,
                summary: parseSummary(article.content)
            };
        }
    }

    return {
        scores: searchResults,
        bestMatch
    };
}