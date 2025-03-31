// Define unit category types
export type UnitCategory =
    'length' | 'area' | 'volume' | 'mass' | 'time' | 'speed' | 'temperature' |
    'energy' | 'frequency' | 'data' | 'pressure' | 'angle' | 'fuel' | 'dataTransferRate';

export interface UnitConversion {
    multiplier: number;
    offset?: number; // For temperature conversions
    decimals: number;
    invert?: boolean; // For special cases like fuel efficiency
}

export interface UnitSystem {
    [unit: string]: UnitConversion;
}

export interface UnitCategories {
    [category: string]: UnitSystem;
}

export const UNITS: UnitCategories = {
    length: {
        // Metric
        millimeters: { multiplier: 1000, decimals: 1 },
        centimeters: { multiplier: 100, decimals: 1 },
        meters: { multiplier: 1, decimals: 2 },
        kilometers: { multiplier: 0.001, decimals: 3 },
        // Imperial/US
        inches: { multiplier: 39.3701, decimals: 2 },
        feet: { multiplier: 3.28084, decimals: 2 },
        yards: { multiplier: 1.09361, decimals: 2 },
        miles: { multiplier: 0.000621371, decimals: 4 },
        // Other
        nauticalMiles: { multiplier: 0.000539957, decimals: 4 },
        lightYears: { multiplier: 1.057e-16, decimals: 20 },
        astronomicalUnits: { multiplier: 6.68459e-12, decimals: 14 },
        parsecs: { multiplier: 3.24078e-17, decimals: 20 }
    },

    area: {
        // Metric
        squareMillimeters: { multiplier: 1000000, decimals: 0 },
        squareCentimeters: { multiplier: 10000, decimals: 0 },
        squareMeters: { multiplier: 1, decimals: 2 },
        squareKilometers: { multiplier: 0.000001, decimals: 6 },
        hectares: { multiplier: 0.0001, decimals: 4 },
        // Imperial/US
        squareInches: { multiplier: 1550, decimals: 0 },
        squareFeet: { multiplier: 10.7639, decimals: 2 },
        squareYards: { multiplier: 1.19599, decimals: 2 },
        squareMiles: { multiplier: 3.86102e-7, decimals: 9 },
        acres: { multiplier: 0.000247105, decimals: 6 }
    },

    volume: {
        // Metric
        cubicMillimeters: { multiplier: 1000000000, decimals: 0 },
        cubicCentimeters: { multiplier: 1000000, decimals: 0 },
        cubicMeters: { multiplier: 1, decimals: 3 },
        liters: { multiplier: 1000, decimals: 2 },
        milliliters: { multiplier: 1000000, decimals: 0 },
        // Imperial/US
        cubicInches: { multiplier: 61023.7, decimals: 0 },
        cubicFeet: { multiplier: 35.3147, decimals: 2 },
        cubicYards: { multiplier: 1.30795, decimals: 2 },
        gallonsUS: { multiplier: 264.172, decimals: 2 },
        gallonsUK: { multiplier: 219.969, decimals: 2 },
        quartsUS: { multiplier: 1056.69, decimals: 2 },
        pintsUS: { multiplier: 2113.38, decimals: 0 },
        cupsUS: { multiplier: 4226.75, decimals: 0 },
        fluidOuncesUS: { multiplier: 33814, decimals: 0 }
    },

    mass: {
        // Metric
        milligrams: { multiplier: 1000000, decimals: 0 },
        grams: { multiplier: 1000, decimals: 0 },
        kilograms: { multiplier: 1, decimals: 2 },
        metricTons: { multiplier: 0.001, decimals: 4 },
        // Imperial/US
        ounces: { multiplier: 35.274, decimals: 2 },
        pounds: { multiplier: 2.20462, decimals: 2 },
        stones: { multiplier: 0.157473, decimals: 3 },
        shortTons: { multiplier: 0.00110231, decimals: 6 },
        longTons: { multiplier: 0.000984207, decimals: 6 },
        // Other
        carats: { multiplier: 5000, decimals: 0 },
        grains: { multiplier: 15432.4, decimals: 0 }
    },

    time: {
        // Standard
        milliseconds: { multiplier: 86400000, decimals: 0 },
        seconds: { multiplier: 86400, decimals: 0 },
        minutes: { multiplier: 1440, decimals: 1 },
        hours: { multiplier: 24, decimals: 1 },
        days: { multiplier: 1, decimals: 2 },
        weeks: { multiplier: 1 / 7, decimals: 2 },
        months: { multiplier: 1 / 30.44, decimals: 2 },
        years: { multiplier: 1 / 365.25, decimals: 3 },
        decades: { multiplier: 1 / 3652.5, decimals: 4 },
        centuries: { multiplier: 1 / 36525, decimals: 5 },
        millennia: { multiplier: 1 / 365250, decimals: 6 }
    },

    speed: {
        metersPerSecond: { multiplier: 1, decimals: 2 },
        kilometersPerHour: { multiplier: 3.6, decimals: 1 },
        milesPerHour: { multiplier: 2.23694, decimals: 2 },
        feetPerSecond: { multiplier: 3.28084, decimals: 2 },
        knots: { multiplier: 1.94384, decimals: 2 },
        mach: { multiplier: 0.00293858, decimals: 4 }, // at sea level, 15°C
        speedOfLight: { multiplier: 3.33564e-9, decimals: 12 } // in vacuum
    },

    temperature: {
        // Special case with offsets
        celsius: { multiplier: 1, offset: 0, decimals: 1 },
        fahrenheit: { multiplier: 1.8, offset: 32, decimals: 1 },
        kelvin: { multiplier: 1, offset: 273.15, decimals: 1 },
        rankine: { multiplier: 1.8, offset: 491.67, decimals: 1 }
    },

    energy: {
        joules: { multiplier: 1, decimals: 2 },
        kilojoules: { multiplier: 0.001, decimals: 3 },
        calories: { multiplier: 0.239006, decimals: 2 },
        kilocalories: { multiplier: 0.000239006, decimals: 6 },
        wattHours: { multiplier: 0.000277778, decimals: 6 },
        kilowattHours: { multiplier: 2.77778e-7, decimals: 9 },
        btu: { multiplier: 0.000947817, decimals: 6 },
        electronvolts: { multiplier: 6.242e+18, decimals: 0 },
        footPounds: { multiplier: 0.737562, decimals: 2 }
    },

    pressure: {
        pascals: { multiplier: 1, decimals: 0 },
        hectopascals: { multiplier: 0.01, decimals: 2 },
        kilopascals: { multiplier: 0.001, decimals: 3 },
        bar: { multiplier: 1e-5, decimals: 5 },
        atmospheres: { multiplier: 9.86923e-6, decimals: 6 },
        torr: { multiplier: 0.00750062, decimals: 5 },
        psi: { multiplier: 0.000145038, decimals: 6 }
    },

    data: {
        bits: { multiplier: 8, decimals: 0 },
        bytes: { multiplier: 1, decimals: 0 },
        kilobytes: { multiplier: 0.001, decimals: 3 },
        megabytes: { multiplier: 1e-6, decimals: 6 },
        gigabytes: { multiplier: 1e-9, decimals: 9 },
        terabytes: { multiplier: 1e-12, decimals: 12 },
        petabytes: { multiplier: 1e-15, decimals: 15 },
        kibibytes: { multiplier: 0.0009765625, decimals: 6 },
        mebibytes: { multiplier: 9.53674e-7, decimals: 9 },
        gibibytes: { multiplier: 9.31323e-10, decimals: 12 },
        tebibytes: { multiplier: 9.09495e-13, decimals: 15 }
    },

    angle: {
        degrees: { multiplier: 1, decimals: 2 },
        radians: { multiplier: 0.0174533, decimals: 4 },
        gradians: { multiplier: 1.11111, decimals: 2 },
        arcminutes: { multiplier: 60, decimals: 0 },
        arcseconds: { multiplier: 3600, decimals: 0 },
        revolutions: { multiplier: 0.00277778, decimals: 5 }
    },
    
    frequency: {
        hertz: { multiplier: 1, decimals: 2 },
        kilohertz: { multiplier: 0.001, decimals: 4 },
        megahertz: { multiplier: 1e-6, decimals: 6 },
        gigahertz: { multiplier: 1e-9, decimals: 9 },
        revolutionsPerMinute: { multiplier: 60, decimals: 2 },
        beatsPerMinute: { multiplier: 60, decimals: 2 }
    },

    fuel: {
        milesPerGallon: { multiplier: 1, decimals: 2 },
        kilometersPerLiter: { multiplier: 0.425144, decimals: 2 },
        litersPer100km: { multiplier: 235.215, decimals: 1, invert: true },
        milesPerLiter: { multiplier: 0.264172, decimals: 2 }
    },
    
    dataTransferRate: {
        bitsPerSecond: { multiplier: 1, decimals: 0 },
        kilobitsPerSecond: { multiplier: 0.001, decimals: 3 },
        megabitsPerSecond: { multiplier: 1e-6, decimals: 6 },
        gigabitsPerSecond: { multiplier: 1e-9, decimals: 9 },
        bytesPerSecond: { multiplier: 0.125, decimals: 3 },
        kilobytesPerSecond: { multiplier: 0.000125, decimals: 6 },
        megabytesPerSecond: { multiplier: 1.25e-7, decimals: 9 },
        gigabytesPerSecond: { multiplier: 1.25e-10, decimals: 12 }
    }
};

export const CATEGORY_NAMES: Record<string, string> = {
    length: 'Length',
    area: 'Area',
    volume: 'Volume',
    mass: 'Mass / Weight',
    time: 'Time',
    speed: 'Speed / Velocity',
    temperature: 'Temperature',
    energy: 'Energy',
    frequency: 'Frequency',
    data: 'Digital Storage',
    angle: 'Plane Angle',
    pressure: 'Pressure',
    fuel: 'Fuel Economy',
    dataTransferRate: 'Data Transfer Rate'
};

export const UNIT_DISPLAY_NAMES: Record<string, string> = {
    // Length
    millimeters: 'Millimeters (mm)',
    centimeters: 'Centimeters (cm)',
    meters: 'Meters (m)',
    kilometers: 'Kilometers (km)',
    inches: 'Inches (in)',
    feet: 'Feet (ft)',
    yards: 'Yards (yd)',
    miles: 'Miles (mi)',
    nauticalMiles: 'Nautical Miles',
    lightYears: 'Light Years',
    astronomicalUnits: 'Astronomical Units (AU)',
    parsecs: 'Parsecs (pc)',

    // Area
    squareMillimeters: 'Square Millimeters (mm²)',
    squareCentimeters: 'Square Centimeters (cm²)',
    squareMeters: 'Square Meters (m²)',
    squareKilometers: 'Square Kilometers (km²)',
    hectares: 'Hectares (ha)',
    squareInches: 'Square Inches (in²)',
    squareFeet: 'Square Feet (ft²)',
    squareYards: 'Square Yards (yd²)',
    squareMiles: 'Square Miles (mi²)',
    acres: 'Acres',

    // Volume
    cubicMillimeters: 'Cubic Millimeters (mm³)',
    cubicCentimeters: 'Cubic Centimeters (cm³)',
    cubicMeters: 'Cubic Meters (m³)',
    liters: 'Liters (L)',
    milliliters: 'Milliliters (mL)',
    cubicInches: 'Cubic Inches (in³)',
    cubicFeet: 'Cubic Feet (ft³)',
    cubicYards: 'Cubic Yards (yd³)',
    gallonsUS: 'Gallons (US)',
    gallonsUK: 'Gallons (UK)',
    quartsUS: 'Quarts (US)',
    pintsUS: 'Pints (US)',
    cupsUS: 'Cups (US)',
    fluidOuncesUS: 'Fluid Ounces (US)',

    // Mass
    milligrams: 'Milligrams (mg)',
    grams: 'Grams (g)',
    kilograms: 'Kilograms (kg)',
    metricTons: 'Metric Tons (t)',
    ounces: 'Ounces (oz)',
    pounds: 'Pounds (lb)',
    stones: 'Stones',
    shortTons: 'Short Tons (US)',
    longTons: 'Long Tons (UK)',
    carats: 'Carats (ct)',
    grains: 'Grains',

    // Time
    milliseconds: 'Milliseconds (ms)',
    seconds: 'Seconds (s)',
    minutes: 'Minutes (min)',
    hours: 'Hours (h)',
    days: 'Days',
    weeks: 'Weeks',
    months: 'Months',
    years: 'Years',
    decades: 'Decades',
    centuries: 'Centuries',
    millennia: 'Millennia',

    // Speed
    metersPerSecond: 'Meters per Second (m/s)',
    kilometersPerHour: 'Kilometers per Hour (km/h)',
    milesPerHour: 'Miles per Hour (mph)',
    feetPerSecond: 'Feet per Second (ft/s)',
    knots: 'Knots',
    mach: 'Mach',
    speedOfLight: 'Speed of Light (c)',

    // Temperature
    celsius: 'Celsius (°C)',
    fahrenheit: 'Fahrenheit (°F)',
    kelvin: 'Kelvin (K)',
    rankine: 'Rankine (°R)',

    // Energy
    joules: 'Joules (J)',
    kilojoules: 'Kilojoules (kJ)',
    calories: 'Calories (cal)',
    kilocalories: 'Kilocalories (kcal)',
    wattHours: 'Watt-hours (Wh)',
    kilowattHours: 'Kilowatt-hours (kWh)',
    btu: 'BTU',
    electronvolts: 'Electronvolts (eV)',
    footPounds: 'Foot-pounds',

    // Pressure
    pascals: 'Pascals (Pa)',
    hectopascals: 'Hectopascals (hPa)',
    kilopascals: 'Kilopascals (kPa)',
    bar: 'Bar',
    atmospheres: 'Atmospheres (atm)',
    torr: 'Torr (mmHg)',
    psi: 'PSI',

    // Data
    bits: 'Bits',
    bytes: 'Bytes (B)',
    kilobytes: 'Kilobytes (KB)',
    megabytes: 'Megabytes (MB)',
    gigabytes: 'Gigabytes (GB)',
    terabytes: 'Terabytes (TB)',
    petabytes: 'Petabytes (PB)',
    kibibytes: 'Kibibytes (KiB)',
    mebibytes: 'Mebibytes (MiB)',
    gibibytes: 'Gibibytes (GiB)',
    tebibytes: 'Tebibytes (TiB)',

    // Angle (Plane Angle)
    degrees: 'Degrees (°)',
    radians: 'Radians (rad)',
    gradians: 'Gradians (gon)',
    arcminutes: 'Arc Minutes',
    arcseconds: 'Arc Seconds',
    revolutions: 'Revolutions (rev)',

    // Frequency
    hertz: 'Hertz (Hz)',
    kilohertz: 'Kilohertz (kHz)',
    megahertz: 'Megahertz (MHz)',
    gigahertz: 'Gigahertz (GHz)',
    revolutionsPerMinute: 'Revolutions per Minute (RPM)',
    beatsPerMinute: 'Beats per Minute (BPM)',

    // Fuel Economy
    milesPerGallon: 'Miles per Gallon (MPG)',
    kilometersPerLiter: 'Kilometers per Liter (km/L)',
    litersPer100km: 'Liters per 100km (L/100km)',
    milesPerLiter: 'Miles per Liter (mi/L)',
    
    // Data Transfer Rate
    bitsPerSecond: 'Bits per Second (bps)',
    kilobitsPerSecond: 'Kilobits per Second (kbps)',
    megabitsPerSecond: 'Megabits per Second (Mbps)',
    gigabitsPerSecond: 'Gigabits per Second (Gbps)',
    bytesPerSecond: 'Bytes per Second (B/s)',
    kilobytesPerSecond: 'Kilobytes per Second (KB/s)',
    megabytesPerSecond: 'Megabytes per Second (MB/s)',
    gigabytesPerSecond: 'Gigabytes per Second (GB/s)'
};

export function convertUnit(
    value: number,
    fromUnit: string,
    toUnit: string,
    category: string
): number | null {
    const unitSystem = UNITS[category];
    if (!unitSystem) return null;

    const fromConversion = unitSystem[fromUnit];
    const toConversion = unitSystem[toUnit];

    if (!fromConversion || !toConversion) return null;

    if (category === 'temperature') {
        let kelvin: number;

        if (fromUnit === 'celsius') {
            kelvin = value + 273.15;
        } else if (fromUnit === 'fahrenheit') {
            kelvin = (value - 32) / 1.8 + 273.15;
        } else if (fromUnit === 'kelvin') {
            kelvin = value;
        } else if (fromUnit === 'rankine') {
            kelvin = value / 1.8;
        } else {
            return null;
        }

        if (toUnit === 'celsius') {
            return kelvin - 273.15;
        } else if (toUnit === 'fahrenheit') {
            return (kelvin - 273.15) * 1.8 + 32;
        } else if (toUnit === 'kelvin') {
            return kelvin;
        } else if (toUnit === 'rankine') {
            return kelvin * 1.8;
        } else {
            return null;
        }
    }

    // Special handling for fuel efficiency (L/100km) which works inversely
    if (category === 'fuel' && (fromUnit === 'litersPer100km' || toUnit === 'litersPer100km')) {
        if (fromUnit === 'litersPer100km' && toUnit === 'litersPer100km') {
            return value;
        } else if (fromUnit === 'litersPer100km') {
            // Converting from L/100km to another unit
            const baseValue = 100 / value; // Convert to km/L first
            return baseValue * toConversion.multiplier;
        } else if (toUnit === 'litersPer100km') {
            // Converting to L/100km from another unit
            const kmPerLiter = value / fromConversion.multiplier;
            return 100 / kmPerLiter;
        }
    }

    const baseUnitValue = value / fromConversion.multiplier;
    return baseUnitValue * toConversion.multiplier;
}
