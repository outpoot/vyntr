import { error } from '@sveltejs/kit';
import { auth } from '$lib/auth';
import type { RequestEvent } from '@sveltejs/kit';

export async function requireAdmin(event: RequestEvent) {
    const session = await auth.api.getSession({
        headers: event.request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    if (!session.user.isAdmin) {
        throw error(403, 'Not authorized');
    }

    return session.user;
}
