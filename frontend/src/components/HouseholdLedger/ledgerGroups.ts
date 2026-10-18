import type {LedgerEntry, LedgerPeriod} from '../../services/vyvow';

export const localDate = (date = new Date()) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

export function convertedAmount(entry: LedgerEntry, currency: string): number | null {
    if (entry.currency === currency) return entry.amount;
    if (!(entry.rate! > 0) || !(entry.targetRate! > 0)) return null;
    return Math.round(entry.amount / entry.rate! * entry.targetRate! * 100) / 100;
}

export function groupEntries(entries: LedgerEntry[], period: LedgerPeriod) {
    const groups = new Map<string, LedgerEntry[]>();
    const sorted = [...entries].sort((a, b) => b.createdAt.localeCompare(a.createdAt) || b.id - a.id);
    for (const entry of sorted) {
        let key = entry.createdAt.slice(0, 10);
        if (period === 'monthly') key = key.slice(0, 7);
        if (period === 'weekly') {
            const date = new Date(`${key}T12:00:00`);
            date.setDate(date.getDate() - (date.getDay() + 6) % 7);
            key = localDate(date);
        }
        groups.set(key, [...(groups.get(key) || []), entry]);
    }
    return [...groups.entries()];
}
