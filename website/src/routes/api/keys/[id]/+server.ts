import { json, error } from '@sveltejs/kit';
import { auth } from '$lib/auth';
import type { RequestHandler } from './$types';

export const DELETE: RequestHandler = async (event) => {
    const session = await auth.api.getSession({
        headers: event.request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    const result = await auth.api.deleteApiKey({
        body: {
            keyId: event.params.id
        },
        headers: event.request.headers
    });

    return json(result);
};