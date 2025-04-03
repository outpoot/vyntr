const API_BASE = 'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1';

const ratesCache = new Map<string, { date: string; rates: Record<string, number> }>();
const currenciesCache: Record<string, string> | null = null;
let lastUpdateTimestamp: string | null = null;

export async function getAllCurrencies(): Promise<Record<string, string>> {
    if (currenciesCache) return currenciesCache;

    try {
        const response = await fetch(`${API_BASE}/currencies.min.json`);
        if (!response.ok) throw new Error(`API returned status ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`Error fetching currencies:`, error);
        return {};
    }
}

async function fetchRates(currencyCode: string): Promise<{ date: string; rates: Record<string, number> } | null> {
    try {
        const response = await fetch(`${API_BASE}/currencies/${currencyCode.toLowerCase()}.json`);
        if (!response.ok) throw new Error(`API returned status ${response.status} for ${currencyCode}`);
        const data = await response.json();

        const date = new Date().toISOString().split('T')[0];
        return {
            date,
            rates: data[currencyCode.toLowerCase()]
        };
    } catch (error) {
        console.error(`Error fetching rates for ${currencyCode}:`, error);
        return null;
    }
}

export async function updateAllRates() {
    console.log('Starting currency rates update...');

    const currencies = await getAllCurrencies();
    if (!currencies) {
        console.error('Failed to fetch currencies');
        return null;
    }

    const currencyCodes = Object.keys(currencies);
    let success = 0;
    let failed = 0;

    const BATCH_SIZE = 5;
    for (let i = 0; i < currencyCodes.length; i += BATCH_SIZE) {
        const batch = currencyCodes.slice(i, i + BATCH_SIZE);

        await Promise.all(batch.map(async (code) => {
            const rateData = await fetchRates(code);
            if (!rateData) {
                console.error(`Failed to update ${code}`);
                failed++;
            } else {
                ratesCache.set(code.toLowerCase(), rateData);
                success++;
            }
        }));

        if (i + BATCH_SIZE < currencyCodes.length) {
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }

    lastUpdateTimestamp = new Date().toISOString();
    console.log(`Currency update completed: ${success} successful, ${failed} failed`);
    return lastUpdateTimestamp;
}

export async function getRates(currencyCode: string): Promise<{ date: string; rates: Record<string, number> } | null> {
    const code = currencyCode.toLowerCase();

    if (ratesCache.has(code)) {
        return ratesCache.get(code)!;
    }

    const rateData = await fetchRates(code);
    if (rateData) {
        ratesCache.set(code, rateData);
    }
    return rateData;
}

export async function getConversionRate(fromCurrency: string, toCurrency: string): Promise<number | null> {
    const from = fromCurrency.toLowerCase();
    const to = toCurrency.toLowerCase();

    if (from === to) return 1.0;

    const fromRates = await getRates(from);
    if (fromRates && fromRates.rates[to] !== undefined) {
        return fromRates.rates[to];
    }

    const toRates = await getRates(to);
    if (toRates && toRates.rates[from] !== undefined) {
        return 1 / toRates.rates[from];
    }

    const usdRates = await getRates('usd');
    if (usdRates) {
        const fromToUsd = usdRates.rates[from] ? 1 / usdRates.rates[from] : null;
        const usdToTo = usdRates.rates[to];

        if (fromToUsd && usdToTo) {
            return fromToUsd * usdToTo;
        }
    }

    return null;
}

export function getLastUpdateTimestamp(): string | null {
    return lastUpdateTimestamp;
}

export function initCurrencyStore() {
    console.log('Currency store initialized');

    getRates('usd').catch(err => console.error('Failed to fetch USD rates:', err));
    getRates('eur').catch(err => console.error('Failed to fetch EUR rates:', err));
    getRates('btc').catch(err => console.error('Failed to fetch BTC rates:', err));

    lastUpdateTimestamp = new Date().toISOString();
}
