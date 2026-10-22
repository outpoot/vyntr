import { initCurrencyStore, updateAllRates } from '$lib/utils/currencyApi';
import { auth } from "$lib/auth";
import { svelteKitHandler } from "better-auth/svelte-kit";
import { initCronJobs } from '$lib/server/summaries';

let initialized = false;
if (!initialized) {
    console.log('Initializing currency store...');
    initCurrencyStore();
    // initCronJobs().catch(console.error);

    // TODO: cron job at 00:00 utc or smth like that instead
    setInterval(() => {
        console.log('Running scheduled currency update');
        updateAllRates().catch(err => {
            console.error('Scheduled currency update failed:', err);
        });
    }, 24 * 60 * 60 * 1000);

    initialized = true;
}

const WRITE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

export async function handle({ event, resolve }) {
    const path = event.url.pathname;
    if (path.startsWith('/api/') && !path.startsWith('/api/auth') && WRITE_METHODS.has(event.request.method)) {
        try {
            const session = await auth.api.getSession({ headers: event.request.headers });
            if ((session?.user as { isBanned?: boolean } | undefined)?.isBanned) {
                return new Response(JSON.stringify({ message: 'This account is suspended' }), {
                    status: 403,
                    headers: { 'Content-Type': 'application/json' }
                });
            }
        } catch {
        }
    }

    // event.setHeaders({
    //     'Cache-Control': 'private, no-cache, no-store, must-revalidate'
    // });

    return svelteKitHandler({ event, resolve, auth });
}
