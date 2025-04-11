import { auth } from '$lib/auth';
import { db } from '$lib/server/db';
import { userPreferences } from '$lib/server/schema';
import { eq } from 'drizzle-orm';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async (event) => {
    const sessionResponse = await auth.api.getSession({
        headers: event.request.headers
    });

    let preferences = {
        safeSearch: true,
        autocomplete: true,
        instantResults: true,
        aiSummarise: true,
        analyticsEnabled: true,
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
            };
        }
    }

    return {
        userSession: sessionResponse?.user || null,
        url: event.url.pathname,
        preferences
    };
};