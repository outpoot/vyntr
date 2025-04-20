import type { PageServerLoad } from './$types';
import { db } from '$lib/server/db';
import { userPreferences, apikey, apiusage, dailyMessageUsage, website } from '$lib/server/schema';
import { eq } from 'drizzle-orm';
import { auth } from '$lib/auth';

export const load = (async ({ locals, request }) => {
    const session = await auth.api.getSession({ headers: request.headers });
    if (!session?.user.id) return {
        preferences: {
            preferredLanguage: 'en',
            safeSearch: true,
            autocomplete: true,
            instantResults: true,
            aiSummarise: true,
            anonymousQueries: true,
            analyticsEnabled: true,
            aiPersonalization: true
        }
    };

    const userId = session.user.id;

    const [
        preferences,
        websites,
        apiKeys,
        apiUsage,
        messageUsage
    ] = await Promise.all([
        db.query.userPreferences.findFirst({
            where: eq(userPreferences.userId, userId)
        }),
        db.query.website.findMany({
            where: eq(website.userId, userId)
        }),
        db.query.apikey.findMany({
            where: eq(apikey.userId, userId),
            columns: {
                id: true,
                name: true,
                prefix: true,
                enabled: true,
                createdAt: true,
                // Excluding sensitive fields like 'key'
            }
        }),
        db.query.apiusage.findMany({
            where: eq(apiusage.userId, userId)
        }),
        db.query.dailyMessageUsage.findMany({
            where: eq(dailyMessageUsage.userId, userId)
        })
    ]);

    return {
        preferences: {
            preferredLanguage: 'en',
            safeSearch: true,
            autocomplete: true,
            instantResults: true,
            aiSummarise: true,
            anonymousQueries: true,
            analyticsEnabled: true,
            aiPersonalization: true,
            ...preferences
        },
        websites,
        apiKeys,
        apiUsage,
        messageUsage
    };
}) satisfies PageServerLoad;
