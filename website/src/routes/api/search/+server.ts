import { error, json } from '@sveltejs/kit';
import { searchBliptext } from '$lib/server/bliptext';
import { parseDateQuery } from '$lib/utils/date';
import { formatTimeDifference, TIME_UNITS } from '$lib/utils/time';
import { searchWordnet } from '$lib/server/wordnet';
import { parseCurrencyQuery, performConversion } from '$lib/utils/currency';
import { parseUnitQuery } from '$lib/utils/unitParser';
import { convertUnit, UNITS } from '$lib/utils/units';
import { auth } from '$lib/auth';
import { db } from '$lib/server/db';
import { apiusage, apikey } from '$lib/server/schema';
import { eq, and } from 'drizzle-orm';
import { SEARCH_ENDPOINT } from '$env/static/private';
import { getFavicon } from '$lib/utils';

async function fetchSearchResults(query: string) {
    try {
        const encodedQuery = encodeURIComponent(query);
        const response = await fetch(`${SEARCH_ENDPOINT}${encodedQuery}`);
        const data = await response.json();

        return data.results.map((result: any) => ({
            favicon: getFavicon(result.url),
            title: result.title,
            url: result.url,
            pageTitle: result.title,
            date: result.date || new Date().toISOString(),
            preview: result.meta_description || '',
            score: result.score
        }));
    } catch (err) {
        console.error('Search API error:', err);
        return [];
    }
}

export async function GET({ url, request }) {
    const authHeader = request.headers.get('Authorization');
    let userId = null;

    if (authHeader?.startsWith('Bearer ')) {
        const apiKeyStr = authHeader.substring(7);
        const { valid, error: verifyError, key } = await auth.api.verifyApiKey({
            body: { key: apiKeyStr }
        });

        if (verifyError || !valid || !key) {
            throw error(401, 'Invalid API key');
        }

        // Get the user ID from the API key record
        const keyRecord = await db.select()
            .from(apikey)
            .where(eq(apikey.id, key.id))
            .limit(1);

        if (!keyRecord.length) {
            throw error(401, 'Invalid API key');
        }

        userId = keyRecord[0].userId;

        // Track API usage
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

    const query = url.searchParams.get('q');
    if (!query) {
        throw error(400, 'Query parameter "q" is required');
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
    const webResults = await fetchSearchResults(query);

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

    return json({
        web: webResults,
        bliptext: bliptextDetail,
        date: dateDetail,
        word: wordDetail,
        currency: currencyDetail,
        unitConversion: unitConversionDetail
    });
}