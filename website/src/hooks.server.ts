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

export async function handle({ event, resolve }) {
    // event.setHeaders({
    //     'Cache-Control': 'private, no-cache, no-store, must-revalidate'
    // });

    return svelteKitHandler({ event, resolve, auth });
}
