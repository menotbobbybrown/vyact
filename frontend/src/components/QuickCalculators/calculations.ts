const DAY_MS = 86_400_000;

export function calculateReturn(base: string, current: string, years?: string): number | null {
    if (base === '' || current === '' || !Number.isFinite(Number(base)) || !Number.isFinite(Number(current))
        || Number(base) <= 0 || Number(current) < 0
        || (years !== undefined && (years === '' || !Number.isFinite(Number(years)) || Number(years) <= 0))) return null;
    const ratio = Number(current) / Number(base);
    const result = (years === undefined ? ratio - 1 : Math.pow(ratio, 1 / Number(years)) - 1) * 100;
    return Number.isFinite(result) ? result : null;
}

export function calculateTripDays(start: string, end: string, inclusive: boolean): number | null {
    const from = Date.parse(start);
    const to = Date.parse(end);
    return Number.isFinite(from) && Number.isFinite(to) && to >= from
        ? Math.round((to - from) / DAY_MS) + Number(inclusive) : null;
}

export function calculateArrival(start: string, days: string, inclusive: boolean): number | null {
    if (days === '' || !Number.isInteger(Number(days)) || Number(days) < Number(inclusive)) return null;
    const result = Date.parse(start) + (Number(days) - Number(inclusive)) * DAY_MS;
    return Number.isFinite(result) && Math.abs(result) <= 8.64e15 ? result : null;
}
