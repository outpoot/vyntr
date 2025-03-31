import { UNITS, type UnitCategory, UNIT_DISPLAY_NAMES } from './units';

export interface UnitConversionQuery {
    value: number;
    fromUnit: string;
    toUnit: string;
    category: UnitCategory;
}

const CONVERSION_PATTERNS = [
    // "convert Xunit to Yunit" or "convert X unit to Y unit"
    /convert\s+(\d+(?:\.\d+)?)\s*([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+to\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)/i,
    // "Xunit to Yunit" or "X unit to Y unit"
    /(\d+(?:\.\d+)?)\s*([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+to\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)/i,
    // "Xunit in Yunit" or "X unit in Y unit"
    /(\d+(?:\.\d+)?)\s*([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+in\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)/i,
    // "how many Yunit in Xunit" or "how many Y unit in X unit"
    /how\s+many\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+in\s+(\d+(?:\.\d+)?)\s*([a-zA-Z]+(?:\s+[a-zA-Z]+)*)/i,
];

const UNIT_ALIASES: Record<string, string> = {
    // Length
    'mm': 'millimeters',
    'cm': 'centimeters',
    'm': 'meters',
    'km': 'kilometers',
    'in': 'inches',
    'inch': 'inches',
    'ft': 'feet',
    'foot': 'feet',
    'yd': 'yards',
    'yard': 'yards',
    'mi': 'miles',
    'mile': 'miles',
    'nm': 'nauticalMiles',
    'nautical mile': 'nauticalMiles',
    'light year': 'lightYears',
    'light years': 'lightYears',
    'au': 'astronomicalUnits',
    'pc': 'parsecs',
    'parsec': 'parsecs',

    // Area
    'mm²': 'squareMillimeters',
    'cm²': 'squareCentimeters',
    'm²': 'squareMeters',
    'km²': 'squareKilometers',
    'ha': 'hectares',
    'hectare': 'hectares',
    'in²': 'squareInches',
    'ft²': 'squareFeet',
    'yd²': 'squareYards',
    'mi²': 'squareMiles',
    'acre': 'acres',

    // Data Storage & Transfer
    'bit': 'bits',
    'b': 'bytes',
    'byte': 'bytes',
    'kb': 'kilobytes',
    'mb': 'megabytes',
    'gb': 'gigabytes',
    'tb': 'terabytes',
    'pb': 'petabytes',
    'kib': 'kibibytes',
    'mib': 'mebibytes',
    'gib': 'gibibytes',
    'tib': 'tebibytes',
    'bps': 'bitsPerSecond',
    'kbps': 'kilobitsPerSecond',
    'mbps': 'megabitsPerSecond',
    'gbps': 'gigabitsPerSecond',
    'b/s': 'bytesPerSecond',
    'kb/s': 'kilobytesPerSecond',
    'mb/s': 'megabytesPerSecond',
    'gb/s': 'gigabytesPerSecond',

    // Energy
    'j': 'joules',
    'joule': 'joules',
    'kj': 'kilojoules',
    'cal': 'calories',
    'kcal': 'kilocalories',
    'wh': 'wattHours',
    'kwh': 'kilowattHours',
    'ev': 'electronvolts',

    // Frequency
    'hz': 'hertz',
    'khz': 'kilohertz',
    'mhz': 'megahertz',
    'ghz': 'gigahertz',
    'rpm': 'revolutionsPerMinute',
    'bpm': 'beatsPerMinute',

    // Fuel Economy
    'mpg': 'milesPerGallon',
    'km/l': 'kilometersPerLiter',
    'l/100km': 'litersPer100km',
    'mi/l': 'milesPerLiter',

    // Length already covered above

    // Mass
    'mg': 'milligrams',
    'g': 'grams',
    'kg': 'kilograms',
    't': 'metricTons',
    'oz': 'ounces',
    'lb': 'pounds',
    'lbs': 'pounds',
    'st': 'stones',
    'stone': 'stones',

    // Plane Angle
    'deg': 'degrees',
    '°': 'degrees',
    'rad': 'radians',
    'grad': 'gradians',
    'gon': 'gradians',
    'arcmin': 'arcminutes',
    'arcsec': 'arcseconds',
    'rev': 'revolutions',

    // Pressure
    'pa': 'pascals',
    'hpa': 'hectopascals',
    'kpa': 'kilopascals',
    'atm': 'atmospheres',
    'mmhg': 'torr',
    'psi': 'psi',

    // Speed
    'm/s': 'metersPerSecond',
    'km/h': 'kilometersPerHour',
    'kph': 'kilometersPerHour',
    'mph': 'milesPerHour',
    'fps': 'feetPerSecond',
    'ft/s': 'feetPerSecond',
    'knot': 'knots',

    // Temperature
    'c': 'celsius',
    '°c': 'celsius',
    'celsius': 'celsius',
    'f': 'fahrenheit',
    '°f': 'fahrenheit',
    'k': 'kelvin',
    'r': 'rankine',

    // Time
    'ms': 'milliseconds',
    's': 'seconds',
    'sec': 'seconds',
    'min': 'minutes',
    'h': 'hours',
    'hr': 'hours',
    'd': 'days',
    'w': 'weeks',
    'y': 'years',
    'yr': 'years'
};

export function parseUnitQuery(query: string): UnitConversionQuery | null {
    for (const pattern of CONVERSION_PATTERNS) {
        const match = query.match(pattern);
        if (!match) continue;

        // Handling different pattern formats
        let value: number;
        let fromUnitText: string;
        let toUnitText: string;

        if (pattern === CONVERSION_PATTERNS[3]) {
            // "how many Y unit in X unit" pattern
            toUnitText = match[1].toLowerCase().trim();
            value = parseFloat(match[2]);
            fromUnitText = match[3].toLowerCase().trim();
        } else {
            // Other patterns
            value = parseFloat(match[1]);
            fromUnitText = match[2].toLowerCase().trim();
            toUnitText = match[3].toLowerCase().trim();
        }

        // Map to standardized unit names
        const fromUnit = UNIT_ALIASES[fromUnitText] || fromUnitText;
        const toUnit = UNIT_ALIASES[toUnitText] || toUnitText;

        // Find the category these units belong to
        const category = findUnitCategory(fromUnit, toUnit);
        if (!category) return null;

        return {
            value,
            fromUnit,
            toUnit,
            category
        };
    }

    return null;
}

function findUnitCategory(fromUnit: string, toUnit: string): UnitCategory | null {
    for (const [category, units] of Object.entries(UNITS)) {
        if (units[fromUnit] && units[toUnit]) {
            return category as UnitCategory;
        }
    }
    return null;
}

export function getUnitDisplayName(unit: string): string {
    return UNIT_DISPLAY_NAMES[unit] || unit;
}
