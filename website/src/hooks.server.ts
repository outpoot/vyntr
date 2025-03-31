import { initCurrencyStore, updateAllRates } from '$lib/utils/currencyApi';

let initialized = false;
if (!initialized) {
    console.log('Initializing currency store...');
    initCurrencyStore();

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
    return await resolve(event);
}
