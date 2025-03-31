import type { CurrencySearchDetail } from "$lib/types/searchDetails";
import { getConversionRate, getAllCurrencies, getLastUpdateTimestamp } from "./currencyApi";

const CURRENCY_SYMBOL_MAP: Record<string, string> = {
    '$': 'USD',
    '€': 'EUR',
    '£': 'GBP',
    '¥': 'JPY',
    '₿': 'BTC',
    'Ξ': 'ETH',
    '₮': 'USDT',
    'euro': 'EUR',
};

const symbolPattern = Object.keys(CURRENCY_SYMBOL_MAP)
    .map(symbol => symbol.length > 1 ? symbol : '\\' + symbol)
    .join('|');

const CURRENCY_REGEX = new RegExp(
    `^(\\d*\\.?\\d+)?\\s*(${symbolPattern}|[A-Za-z]{3})\\s*(?:to|in|as)\\s*(${symbolPattern}|[A-Za-z]{3})$`,
    'i'
);

const SINGLE_CURRENCY_REGEX = new RegExp(
    `^(?:(?:price|cost|stock|value|rate|of)\\s*(${symbolPattern}|[A-Za-z]{3})|(${symbolPattern}|[A-Za-z]{3})\\s*(?:price|cost|stock|value|rate|of))$`,
    'i'
);

const DEFAULT_TARGET_CURRENCY = "USD";
const FALLBACK_TARGET_CURRENCY = "EUR";

export interface CurrencyMatch {
    from: {
        code: string;
        amount: number;
    };
    to: {
        code: string;
    };
}

function normalizeCurrencyCode(code: string): string {
    return CURRENCY_SYMBOL_MAP[code.toLowerCase()] || code.toUpperCase();
}

function isValidCurrency(code: string, currencies: Record<string, string>,): boolean {
    return code.toLowerCase() in currencies;
}

function getCurrencyName(code: string, currencies: Record<string, string>,): string {
    return currencies[code.toLowerCase()] || code;
}

export async function parseCurrencyQuery(query: string): Promise<CurrencyMatch | null> {
    const fullMatch = query.match(CURRENCY_REGEX);

    if (fullMatch) {
        const [, amountStr, fromCodeRaw, toCodeRaw] = fullMatch;
        const fromCode = normalizeCurrencyCode(fromCodeRaw);
        const toCode = normalizeCurrencyCode(toCodeRaw);
        const amount = amountStr ? parseFloat(amountStr) : 1;

        const currencies = await getAllCurrencies();

        if (
            !isValidCurrency(fromCode, currencies) ||
            !isValidCurrency(toCode, currencies)
        ) {
            return null;
        }

        return {
            from: { code: fromCode, amount },
            to: { code: toCode },
        };
    }

    const singleMatch = query.match(SINGLE_CURRENCY_REGEX);

    if (singleMatch) {
        const codeRaw = singleMatch[1] || singleMatch[2];
        const fromCode = normalizeCurrencyCode(codeRaw);

        const currencies = await getAllCurrencies();

        if (!isValidCurrency(fromCode, currencies)) {
            return null;
        }

        const targetCurrency =
            fromCode === DEFAULT_TARGET_CURRENCY
                ? FALLBACK_TARGET_CURRENCY
                : DEFAULT_TARGET_CURRENCY;

        return {
            from: { code: fromCode, amount: 1 },
            to: { code: targetCurrency },
        };
    }

    return null;
}

export async function performConversion(
    match: CurrencyMatch,
): Promise<CurrencySearchDetail | null> {
    const rate = await getConversionRate(match.from.code, match.to.code);

    if (rate === null) {
        console.warn(
            `Conversion rate not found for ${match.from.code} to ${match.to.code}`,
        );
        return null;
    }

    const currencies = await getAllCurrencies();
    const lastUpdated = getLastUpdateTimestamp();

    return {
        type: "currency",
        from: {
            code: match.from.code,
            name: getCurrencyName(match.from.code, currencies),
            amount: match.from.amount,
        },
        to: {
            code: match.to.code,
            name: getCurrencyName(match.to.code, currencies),
            amount: match.from.amount * rate,
        },
        rate,
        lastUpdated
    };
}
