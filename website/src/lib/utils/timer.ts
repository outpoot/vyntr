export function parseTimerQuery(query: string): number | null {
    if (/^timer$/i.test(query.trim())) {
        return 60;
    }

    // timer with time specified "30s timer", "timer 30s", "timer 2m", "5m timer", etc.
    const timePattern = /(\d+)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours)/i;
    const match = query.match(timePattern);

    if (match && (query.toLowerCase().includes('timer'))) {
        const value = parseInt(match[1], 10);
        const unit = match[2].toLowerCase();

        if (unit.startsWith('s')) {
            return value;
        } else if (unit.startsWith('m')) {
            return value * 60;
        } else if (unit.startsWith('h')) {
            return value * 3600;
        }
    }

    return null;
}
