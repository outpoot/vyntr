import { error, json, redirect } from '@sveltejs/kit';
import { searchBliptext } from '$lib/server/bliptext';
import { parseDateQuery } from '$lib/utils/date';
import { formatTimeDifference, TIME_UNITS } from '$lib/utils/time';
import { searchWordnet } from '$lib/server/wordnet';
import { parseCurrencyQuery, performConversion } from '$lib/utils/currency';
import { parseUnitQuery } from '$lib/utils/unitParser';
import { convertUnit, UNITS } from '$lib/utils/units';
import { auth } from '$lib/auth';
import { db } from '$lib/server/db';
import { apiusage, apikey, searchQueries, userPreferences } from '$lib/server/schema';
import { eq, and, sql } from 'drizzle-orm';
import { SEARCH_ENDPOINT } from '$env/static/private';
import { getFavicon } from '$lib/utils';
import { BANGS } from '$lib/bangs';

async function fetchSearchResults(query: string, language: string = 'en') {
    try {
        const encodedQuery = encodeURIComponent(query);
        const url = `${SEARCH_ENDPOINT}${encodedQuery}&language=${language}`;
        console.log('Search URL:', url);
        const response = await fetch(url);
        const data = await response.json();

        return data.results.map((result: any) => ({
            favicon: getFavicon(result.url),
            title: result.title,
            url: result.url,
            pageTitle: result.title,
            date: result.date || new Date().toISOString(),
            preview: result.preview || '',
            score: result.score
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

export async function GET({ url, request }) {
    const query = url.searchParams.get('q');
    if (!query) {
        throw error(400, 'Query parameter "q" is required');
    }

    const authHeader = request.headers.get('Authorization');

    let userId = null;
    let userPrefs = null;

    const session = await auth.api.getSession({ headers: request.headers });

    if (session?.user) {
        userId = session.user.id;
        const prefs = await db.query.userPreferences.findFirst({
            where: eq(userPreferences.userId, userId)
        });
        userPrefs = prefs;
    }
    else if (authHeader?.startsWith('Bearer ')) {
        const apiKeyStr = authHeader.substring(7);
        const { valid, error: verifyError, key } = await auth.api.verifyApiKey({
            body: { key: apiKeyStr }
        });

        if (verifyError || !valid || !key) {
            throw error(401, 'Invalid API key');
        }

        const keyRecord = await db.select()
            .from(apikey)
            .where(eq(apikey.id, key.id))
            .limit(1);

        if (!keyRecord.length) {
            throw error(401, 'Invalid API key');
        }

        userId = keyRecord[0].userId;

        // track API usage
        const today = new Date().toISOString().split('T')[0];
        try {
            const existingRecord = await db.select()
                .from(apiusage)
                .where(and(
                    eq(apiusage.date, today),
                    eq(apiusage.userId, userId)
                ))
                .limit(1);

            if (existingRecord.length > 0) {
                await db.update(apiusage)
                    .set({
                        count: existingRecord[0].count + 1,
                        updatedAt: new Date()
                    })
                    .where(eq(apiusage.id, existingRecord[0].id));
            } else {
                await db.insert(apiusage).values({
                    userId,
                    date: today,
                    count: 1,
                    createdAt: new Date(),
                    updatedAt: new Date()
                });
            }
        } catch (err) {
            console.error('Failed to track API usage:', err);
        }
    }

    const language = userPrefs?.preferredLanguage || 'en';

    // log search query
    if (!userPrefs || userPrefs.anonymousQueries) {
        saveSearchQuery(query);
    }

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

    // ==================== WEB SEARCH ====================
    const webResults = await fetchSearchResults(query, language);

    // ==================== BLIPTEXT SEARCH ====================
    const bliptextResults = await searchBliptext(query);
    const bliptextDetail = bliptextResults.bestMatch ? { type: 'bliptext', article: bliptextResults.bestMatch } : null;

    // ==================== WORD LOOKUP ====================
    let wordDetail = null;
    try {
        const matches = await searchWordnet(query);
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

    let aiSummary = null;
    if (!userPrefs || userPrefs.aiSummarise) {
        // TODO: Implement AI summary generation
    }

    return json({
        web: webResults,
        bliptext: bliptextDetail,
        date: dateDetail,
        word: wordDetail,
        currency: currencyDetail,
        unitConversion: unitConversionDetail,
        ai_summary: aiSummary
    });
}