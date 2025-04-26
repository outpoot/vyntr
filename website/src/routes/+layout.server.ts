import { auth } from '$lib/auth';
import { db } from '$lib/server/db';
import { userPreferences } from '$lib/server/schema';
import { eq } from 'drizzle-orm';
import type { LayoutServerLoad } from './$types';
import { dev } from '$app/environment';

export const load: LayoutServerLoad = async (event) => {
    event.setHeaders({
        'Cache-Control': dev 
            ? 'no-cache' 
            : 'private, max-age=30'
    });

    const sessionResponse = await auth.api.getSession({
        headers: event.request.headers
    });

    let preferences = {
        safeSearch: true,
        autocomplete: true,
        instantResults: true,
        aiSummarise: true,
        analyticsEnabled: true,
        excludeNsfw: false,
    };

    if (sessionResponse?.user) {
        const userPrefs = await db.query.userPreferences.findFirst({
            where: eq(userPreferences.userId, sessionResponse.user.id)
        });
        if (userPrefs) {
            preferences = {
                safeSearch: userPrefs.safeSearch,
                autocomplete: userPrefs.autocomplete,
                instantResults: userPrefs.instantResults,
                aiSummarise: userPrefs.aiSummarise,
                analyticsEnabled: userPrefs.analyticsEnabled,
                excludeNsfw: userPrefs.excludeNsfw,
            };
        }
    }

    return {
        userSession: sessionResponse?.user || null,
        url: event.url.pathname,
        preferences
    };
};