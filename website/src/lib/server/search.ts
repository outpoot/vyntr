import { searchBliptext } from '$lib/server/bliptext';
import { parseDateQuery } from '$lib/utils/date';
import { formatTimeDifference, TIME_UNITS } from '$lib/utils/time';
import { searchWordnet } from '$lib/server/wordnet';
import { parseCurrencyQuery, performConversion } from '$lib/utils/currency';
import { parseUnitQuery } from '$lib/utils/unitParser';
import { convertUnit } from '$lib/utils/units';
import { aiSummaries, searchQueries } from '$lib/server/schema';
import { eq, and, sql } from 'drizzle-orm';
import { SEARCH_ENDPOINT } from '$env/static/private';
import { getFavicon } from '$lib/utils';
import { db } from '$lib/server/db';
import { tryCorrectSpelling } from '$lib/server/spellingCorrection';

export async function performSearch(query: string, userPrefs: any = null) {
    const language = userPrefs?.preferredLanguage || 'en';

    // log search query if anonymous queries enabled
    if (!userPrefs || userPrefs.anonymousQueries) {
        saveSearchQuery(query);
    }

    const spellingCorrection = await tryCorrectSpelling(query);

    // ==================== DATE ====================
    const dateResult = parseDateQuery(query);
    const dateDetail = dateResult ? {
        type: 'date',
        value: Number((dateResult.milliseconds * TIME_UNITS[dateResult.unit].multiplier).toFixed(TIME_UNITS[dateResult.unit].decimals)),
        description: dateResult.description,
        date: dateResult.date.toISOString(),
        unit: dateResult.unit,
        displayText: formatTimeDifference(dateResult.milliseconds, dateResult.unit)
    } : null;

    // ==================== UNIT CONVERSION ====================
    let unitConversionDetail = null;
    const unitMatch = parseUnitQuery(query);
    if (unitMatch) {
        const result = convertUnit(unitMatch.value, unitMatch.fromUnit, unitMatch.toUnit, unitMatch.category);
        if (result !== null) {
            unitConversionDetail = {
                type: 'unitConversion',
                ...unitMatch,
                result
            };
        }
    }

    // ==================== AI SUMMARY ====================
    let aiSummary = null;
    if (!userPrefs || userPrefs.aiSummarise) {
        const summary = await db.query.aiSummaries.findFirst({
            where: and(
                eq(aiSummaries.query, query.toLowerCase().trim()),
                eq(aiSummaries.isNull, false)
            )
        });
        if (summary) {
            aiSummary = summary.summary;
        }
    }

    // ==================== WEB SEARCH ====================
    let webQuery = query;
    if (spellingCorrection) {
        // Make use of the OR feature of tantivy
        webQuery = "(" + query + ") OR (" + spellingCorrection.newQuery + ")";
    }
    const webResults = await fetchSearchResults(webQuery, language);

    // ==================== BLIPTEXT SEARCH ====================
    let bliptextResults = await searchBliptext(query);
    // When no results are found, try the corrected spelling
    if ((!bliptextResults.bestMatch) && spellingCorrection) {
        bliptextResults = await searchBliptext(spellingCorrection.newQuery);
    }
    const bliptextDetail = bliptextResults.bestMatch ? { type: 'bliptext', article: bliptextResults.bestMatch } : null;

    // ==================== WORD LOOKUP ====================
    let wordDetail = null;
    try {
        let matches = await searchWordnet(query);

        if (matches.length === 0 && spellingCorrection) {
            matches = await searchWordnet(spellingCorrection.newQuery);
        }

        if (matches.length > 0) {
            const bestMatch = matches[0];
            wordDetail = bestMatch.entry;
        }
    } catch (err) {
        console.error('Word lookup error:', err);
    }

    // ==================== CURRENCY CONVERSION ====================
    let currencyDetail = null;
    const currencyMatch = await parseCurrencyQuery(query);
    if (currencyMatch) {
        currencyDetail = await performConversion(currencyMatch);
    }

    return {
        web: webResults,
        bliptext: bliptextDetail,
        date: dateDetail,
        word: wordDetail,
        currency: currencyDetail,
        unitConversion: unitConversionDetail,
        ai_summary: aiSummary,
        correction: spellingCorrection
    };
}

async function fetchSearchResults(query: string, language: string = 'en') {
    try {
        const encodedQuery = encodeURIComponent(query);
        const url = `${SEARCH_ENDPOINT}${encodedQuery}&language=${language}`;

        const response = await fetch(url);
        const data = await response.json();

        return data.results.map((result: any) => ({
            favicon: getFavicon(result.url),
            title: result.title,
            url: result.url,
            pageTitle: result.title,
            date: result.date || new Date().toISOString(),
            preview: result.preview || '',
            score: result.score,
            nsfw: result.nsfw,
        }));
    } catch (err) {
        console.error('Search API error:', err);
        return [];
    }
}

async function saveSearchQuery(query: string) {
    try {
        const normalizedQuery = query.toLowerCase().trim();
        await db.insert(searchQueries)
            .values({
                query: normalizedQuery,
                count: 1,
            })
            .onConflictDoUpdate({
                target: searchQueries.query,
                set: {
                    count: sql`${searchQueries.count} + 1`,
                    updatedAt: new Date()
                }
            });
    } catch (err) {
        console.error('Failed to log search query:', err);
    }
}