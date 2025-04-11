import { json, error } from '@sveltejs/kit';
import { auth } from '$lib/auth';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async (event) => {
    const session = await auth.api.getSession({
        headers: event.request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    const existingKey = await auth.api.getApiKey({
        query: { id: event.params.id },
        headers: event.request.headers
    });

    if (!existingKey) {
        throw error(404, 'API key not found');
    }

    const newKey = await auth.api.createApiKey({
        body: {
            name: existingKey.name ?? undefined,
            userId: existingKey.userId,
            remaining: existingKey.remaining,
            refillAmount: existingKey.refillAmount ?? undefined,
            refillInterval: existingKey.refillInterval ?? undefined,
            rateLimitEnabled: existingKey.rateLimitEnabled,
            rateLimitTimeWindow: existingKey.rateLimitTimeWindow ?? undefined,
            rateLimitMax: existingKey.rateLimitMax ?? undefined,
            permissions: existingKey.permissions ? JSON.parse(existingKey.permissions) : undefined,
            metadata: existingKey.metadata
        },
        headers: event.request.headers
    });

    await auth.api.deleteApiKey({
        body: { keyId: event.params.id },
        headers: event.request.headers
    });

    return json(newKey);
};
