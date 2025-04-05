import { json, error } from '@sveltejs/kit';
import { auth } from '$lib/auth';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async (event) => {
    const session = await auth.api.getSession({
        headers: event.request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    const keys = await auth.api.listApiKeys({
        headers: event.request.headers
    });

    return json(keys);
};

export const POST: RequestHandler = async (event) => {
    const session = await auth.api.getSession({
        headers: event.request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    const existingKeys = await auth.api.listApiKeys({
        headers: event.request.headers
    });

    if (existingKeys.length > 0) {
        throw error(400, 'You can only have one API key at a time');
    }

    const apiKey = await auth.api.createApiKey({
        body: {
            name: "API Key",
            rateLimitEnabled: true,
            rateLimitTimeWindow: 1000 * 60 * 60 * 24, // 1 day
            rateLimitMax: 1000,
            remaining: 10000, // Initial credit balance
            refillAmount: 1000,
            refillInterval: 1000 * 60 * 60 * 24, // Refill daily
            permissions: {
                api: ['read']
            },
            userId: session.user.id
        },
        headers: event.request.headers
    });

    return json(apiKey);
};
