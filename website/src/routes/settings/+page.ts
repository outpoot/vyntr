import type { PageLoad } from './$types';

export const load = (async ({ fetch }) => {
    const prefResponse = await fetch('/api/user/preferences');
    const preferences = await prefResponse.json();

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
            ...preferences // override defaults with actual user preferences
        }
    };
}) satisfies PageLoad;
