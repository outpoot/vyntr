import { error, json } from '@sveltejs/kit';

import { auth } from '$lib/auth';
import { db } from '$lib/server/db';
import { apiusage, apikey, userPreferences } from '$lib/server/schema';
import { eq, and } from 'drizzle-orm';
import { performSearch } from '$lib/server/search';

export async function GET({ url, request }) {
    const query = url.searchParams.get('q');
    if (!query) {
        throw error(400, 'Query parameter "q" is required');
    }

    const authHeader = request.headers.get('Authorization');
    const session = await auth.api.getSession({ headers: request.headers });

    // Require either a valid session or API key
    if (!session?.user && !authHeader?.startsWith('Bearer ')) {
        throw error(403, 'Authentication required. Sign in or provide an API key.');
    }

    let userId = null;
    let userPrefs = null;

    if (session?.user) {
        userId = session.user.id;
        userPrefs = await db.query.userPreferences.findFirst({
            where: eq(userPreferences.userId, userId)
        });
    } else if (authHeader?.startsWith('Bearer ')) {
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

    const results = await performSearch(query, userPrefs);
    return json(results);
}