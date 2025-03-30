import { TIME_UNITS } from './timeUtils';

type Holiday = {
    name: string;
    getDate: (lookingBack: boolean) => Date;
};

export type TimeUnit = keyof typeof TIME_UNITS;

const UNIT_PATTERN = new RegExp(`\\b(${Object.keys(TIME_UNITS).join('|')})\\b`);
const QUERY_PATTERN = new RegExp(`^(how many )?(${Object.keys(TIME_UNITS).join('|')}) (until|before|to|since|from) `);

// HELPER FUNCTIONS

/**
 * Calculates the date of Easter Sunday for a given year using the
 * Anonymous Gregorian algorithm (Meeus/Jones/Butcher).
 * @param year The year for which to calculate Easter.
 * @returns The date of Easter Sunday.
 */
function getEaster(year: number): Date {
    const a = year % 19;
    const b = Math.floor(year / 100);
    const c = year % 100;
    const d = Math.floor(b / 4);
    const e = b % 4;
    const f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3);
    const h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4);
    const k = c % 4;
    const l = (32 + 2 * e + 2 * i - h - k) % 7;
    const m = Math.floor((a + 11 * h + 22 * l) / 451);
    const month = Math.floor((h + l - 7 * m + 114) / 31); // Month (1-12)
    const day = ((h + l - 7 * m + 114) % 31) + 1; // Day (1-31)
    // JavaScript Date month is 0-indexed (0=Jan, 1=Feb, ...)
    return new Date(year, month - 1, day);
}

/**
 * Calculates the date of the Nth specific weekday of a given month and year.
 * @param n The occurrence (e.g., 1 for 1st, 2 for 2nd).
 * @param dayOfWeek The target day of the week (0=Sun, 1=Mon, ..., 6=Sat).
 * @param month The target month (0=Jan, 1=Feb, ..., 11=Dec).
 * @param year The target year.
 * @returns The date of the Nth weekday.
 */
function getNthDayOfMonth(
    n: number,
    dayOfWeek: number,
    month: number,
    year: number,
): Date {
    const firstOfMonth = new Date(year, month, 1);
    const firstDayOfWeekOfMonth = firstOfMonth.getDay(); // 0-6

    let firstOccurrenceDate = 1 + ((dayOfWeek - firstDayOfWeekOfMonth + 7) % 7);

    let nthOccurrenceDate = firstOccurrenceDate + (n - 1) * 7;

    return new Date(year, month, nthOccurrenceDate);
}

/**
 * Calculates the date of the last specific weekday of a given month and year.
 * @param dayOfWeek The target day of the week (0=Sun, 1=Mon, ..., 6=Sat).
 * @param month The target month (0=Jan, 1=Feb, ..., 11=Dec).
 * @param year The target year.
 * @returns The date of the last weekday.
 */
function getLastDayOfMonth(
    dayOfWeek: number,
    month: number,
    year: number,
): Date {
    const lastDateOfMonth = new Date(year, month + 1, 0); // Day 0 of next month
    const daysInMonth = lastDateOfMonth.getDate();
    const lastDayOfWeekOfMonth = lastDateOfMonth.getDay(); // 0-6

    let diff = lastDayOfWeekOfMonth - dayOfWeek;
    if (diff < 0) {
        diff += 7;
    }

    const dayOfMonth = daysInMonth - diff;
    return new Date(year, month, dayOfMonth);
}

/**
 * Creates a getDate function for fixed-date holidays.
 * Uses UTC for comparison to avoid timezone issues near midnight.
 * @param month The holiday month (0-11).
 * @param day The holiday day (1-31).
 * @returns A function compatible with Holiday['getDate'].
 */
const getDateFixed = (month: number, day: number) => (lookingBack: boolean): Date => {
    const now = new Date();
    const currentYear = now.getFullYear();

    const holidayThisYear = new Date(Date.UTC(currentYear, month, day));
    const nowUtc = new Date(
        Date.UTC(
            now.getUTCFullYear(),
            now.getUTCMonth(),
            now.getUTCDate(),
        ),
    );

    let targetDate: Date;
    if (lookingBack) {
        if (nowUtc < holidayThisYear) {
            // holiday hasn't happened yet this year (UTC), return last year's
            targetDate = new Date(Date.UTC(currentYear - 1, month, day));
        } else {
            // holiday has already happened or is today (UTC), return this year's
            targetDate = holidayThisYear;
        }
    } else {
        // looking forward
        if (nowUtc > holidayThisYear) {
            // holiday has already passed this year (UTC), return next year's
            targetDate = new Date(Date.UTC(currentYear + 1, month, day));
        } else {
            // holiday is today or later this year (UTC), return this year's
            targetDate = holidayThisYear;
        }
    }

    return new Date(
        targetDate.getUTCFullYear(),
        targetDate.getUTCMonth(),
        targetDate.getUTCDate(),
    );
};

/**
 * Creates a getDate function for variable-date holidays.
 * Uses UTC for comparison to avoid timezone issues near midnight.
 * @param calculateDateForYear A function that takes a year and returns the holiday's Date for that year.
 * @returns A function compatible with Holiday['getDate'].
 */
const getDateVariable = (calculateDateForYear: (year: number) => Date) => (lookingBack: boolean): Date => {
    const now = new Date();
    const currentYear = now.getFullYear();

    const holidayThisYear = calculateDateForYear(currentYear);

    const holidayThisYearUtc = new Date(
        Date.UTC(
            holidayThisYear.getFullYear(),
            holidayThisYear.getMonth(),
            holidayThisYear.getDate(),
        ),
    );
    const nowUtc = new Date(
        Date.UTC(
            now.getUTCFullYear(),
            now.getUTCMonth(),
            now.getUTCDate(),
        ),
    );

    if (lookingBack) {
        if (nowUtc < holidayThisYearUtc) {
            // holiday hasn't happened yet this year, return last year's
            return calculateDateForYear(currentYear - 1);
        } else {
            // holiday has already happened or is today, return this year's
            return holidayThisYear;
        }
    } else {
        // looking forward
        if (nowUtc > holidayThisYearUtc) {
            // holiday has already passed this year, return next year's
            return calculateDateForYear(currentYear + 1);
        } else {
            // holiday is today or later this year, return this year's
            return holidayThisYear;
        }
    }
};

// HOLIDAYS

const HOLIDAYS: { [key: string]: Holiday } = {
    // FIXED DATE HOLIDAYS
    'new year': {
        name: "New Year's Day",
        getDate: getDateFixed(0, 1), // Jan 1
    },
    juneteenth: {
        name: 'Juneteenth',
        getDate: getDateFixed(5, 19), // Jun 19
    },
    'valentines': {
        name: "Valentine's Day",
        getDate: getDateFixed(1, 14), // Feb 14
    },
    'st patricks': {
        name: "St. Patrick's Day",
        getDate: getDateFixed(2, 17), // Mar 17
    },
    'april fools': {
        name: "April Fools' Day",
        getDate: getDateFixed(3, 1), // Apr 1
    },
    'canada day': {
        name: 'Canada Day',
        getDate: getDateFixed(6, 1), // Jul 1
    },
    'independence day': {
        name: 'Independence Day (US)',
        getDate: getDateFixed(6, 4), // Jul 4
    },
    halloween: {
        name: 'Halloween',
        getDate: getDateFixed(9, 31), // Oct 31
    },
    'veterans day': {
        name: 'Veterans Day (US)',
        getDate: getDateFixed(10, 11), // Nov 11
    },
    christmas: {
        name: 'Christmas Day',
        getDate: getDateFixed(11, 25), // Dec 25
    },
    'boxing day': {
        name: 'Boxing Day',
        getDate: getDateFixed(11, 26), // Dec 26
    },

    // EASTER-BASED HOLIDAYS (VARIABLE)
    easter: {
        name: 'Easter Sunday',
        getDate: getDateVariable(getEaster),
    },
    'good friday': {
        name: 'Good Friday',
        getDate: getDateVariable((year) => {
            const easterDate = getEaster(year);
            return new Date(
                easterDate.setDate(easterDate.getDate() - 2), // -2 gets us friday
            );
        }),
    },
    'easter monday': {
        name: 'Easter Monday',
        getDate: getDateVariable((year) => {
            const easterDate = getEaster(year);

            return new Date(
                easterDate.setDate(easterDate.getDate() + 1), // +1 gets us monday
            );
        }),
    },

    // UNITED STATES
    'mlk day': {
        name: 'Martin Luther King, Jr. Day',
        getDate: getDateVariable((year) =>
            getNthDayOfMonth(3, 1, 0, year),
        ), // 3rd Mon(1) of Jan(0)
    },
    'presidents day': {
        name: "Presidents' Day (US)",
        getDate: getDateVariable((year) =>
            getNthDayOfMonth(3, 1, 1, year),
        ), // 3rd Mon(1) of Feb(1)
    },
    'mothers day': {
        name: "Mother's Day (US)",
        getDate: getDateVariable((year) =>
            getNthDayOfMonth(2, 0, 4, year),
        ), // 2nd Sun(0) of May(4)
    },
    'memorial day': {
        name: 'Memorial Day (US)',
        getDate: getDateVariable((year) =>
            getLastDayOfMonth(1, 4, year),
        ), // Last Mon(1) of May(4)
    },
    'fathers day': {
        name: "Father's Day (US)",
        getDate: getDateVariable((year) =>
            getNthDayOfMonth(3, 0, 5, year),
        ), // 3rd Sun(0) of Jun(5)
    },
    'labor day': {
        name: 'Labor Day (US)',
        getDate: getDateVariable((year) =>
            getNthDayOfMonth(1, 1, 8, year),
        ), // 1st Mon(1) of Sep(8)
    },
    'columbus day': {
        name: 'Columbus Day / Indigenous Peoples\' Day (US)',
        getDate: getDateVariable((year) =>
            getNthDayOfMonth(2, 1, 9, year),
        ), // 2nd Mon(1) of Oct(9)
    },
    thanksgiving: {
        name: 'Thanksgiving Day (US)',
        getDate: getDateVariable((year) =>
            getNthDayOfMonth(4, 4, 10, year),
        ), // 4th Thu(4) of Nov(10)
    },
};

export function parseDateQuery(query: string): { date: Date; description: string; unit: TimeUnit; milliseconds: number } | null {
    query = query.toLowerCase();
    const lookingBack = query.includes('since') || query.includes('from');

    let unit: TimeUnit = 'days';
    const unitMatch = query.match(UNIT_PATTERN);
    if (unitMatch) {
        unit = unitMatch[1] as TimeUnit;
    } else {
        return null;
    }

    query = query.replace(QUERY_PATTERN, '');

    const createResult = (date: Date, description: string) => {
        const now = new Date();
        const diffTime = date.getTime() - now.getTime();
        return {
            date,
            description,
            unit,
            milliseconds: diffTime
        };
    };

    for (const [key, holiday] of Object.entries(HOLIDAYS)) {
        if (query.includes(key)) {
            return createResult(holiday.getDate(lookingBack), holiday.name);
        }
    }

    if (query === 'tomorrow') {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        return createResult(tomorrow, 'Tomorrow');
    }

    try {
        const date = new Date(query);
        if (!isNaN(date.getTime())) {
            return createResult(date, '');
        }
    } catch {
        return null;
    }

    return null;
}
