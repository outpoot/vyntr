import type { TimeUnit } from './dateUtils';

export const TIME_UNITS = {
    // Extremely small units (10^-30 to 10^-18)
    quectoseconds: { multiplier: 1e30 * 1e9, decimals: 0 },
    rontoseconds: { multiplier: 1e27 * 1e9, decimals: 0 },
    yoctoseconds: { multiplier: 1e24 * 1e9, decimals: 0 },
    zeptoseconds: { multiplier: 1e21 * 1e9, decimals: 0 },
    attoseconds: { multiplier: 1e18 * 1e9, decimals: 0 },

    // Very small units (10^-15 to 10^-9)
    femtoseconds: { multiplier: 1e15 * 1e9, decimals: 0 },
    picoseconds: { multiplier: 1e12 * 1e9, decimals: 0 },
    nanoseconds: { multiplier: 1_000_000, decimals: 0 },

    // Small units (10^-6 to 1)
    microseconds: { multiplier: 1000, decimals: 0 },
    milliseconds: { multiplier: 1, decimals: 0 },
    centiseconds: { multiplier: 1 / 10, decimals: 1 },
    deciseconds: { multiplier: 1 / 100, decimals: 1 },
    seconds: { multiplier: 1 / 1000, decimals: 1 },

    // Medium units
    decaseconds: { multiplier: 1 / 1000 / 10, decimals: 1 },
    minutes: { multiplier: 1 / 1000 / 60, decimals: 1 },
    hours: { multiplier: 1 / 1000 / 60 / 60, decimals: 1 },
    days: { multiplier: 1 / 1000 / 60 / 60 / 24, decimals: 1 },
    weeks: { multiplier: 1 / 1000 / 60 / 60 / 24 / 7, decimals: 1 },
    months: { multiplier: 1 / 1000 / 60 / 60 / 24 / 30.44, decimals: 1 }, // Average month
    years: { multiplier: 1 / 1000 / 60 / 60 / 24 / 365.25, decimals: 1 },

    // Large units
    decades: { multiplier: 1 / 1000 / 60 / 60 / 24 / 365.25 / 10, decimals: 1 },
    centuries: { multiplier: 1 / 1000 / 60 / 60 / 24 / 365.25 / 100, decimals: 1 },
    millennia: { multiplier: 1 / 1000 / 60 / 60 / 24 / 365.25 / 1000, decimals: 1 },

    // Extremely large units
    megaannums: { multiplier: 1 / 1000 / 60 / 60 / 24 / 365.25 / 1e6, decimals: 1 },
    eons: { multiplier: 1 / 1000 / 60 / 60 / 24 / 365.25 / 1e9, decimals: 1 }
};

export function formatTimeDifference(milliseconds: number, unit: TimeUnit): string {
    const absDiff = Math.abs(milliseconds);
    const { multiplier, decimals } = TIME_UNITS[unit];
    const value = absDiff * multiplier;
    const roundedValue = Number(value.toFixed(decimals));

    return `${roundedValue} ${roundedValue === 1 ? unit.slice(0, -1) : unit}${milliseconds < 0 ? ' ago' : ''}`;
}
