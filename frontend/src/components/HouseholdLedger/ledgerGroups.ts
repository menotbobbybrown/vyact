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

export function ledgerTotals(entries: LedgerEntry[], currency: string) {
    let income = 0, expense = 0, missing = false;
    for (const entry of entries) {
        const amount = convertedAmount(entry, currency);
        if (amount === null) {missing = true; continue;}
        if (entry.txType === 'INCOME') income += amount;
        else expense += amount;
    }
    return {income, expense, balance: income - expense, missing};
}

export function categoryGroups(entries: LedgerEntry[], currency: string) {
    const categories = new Map<number, LedgerEntry[]>();
    for (const entry of entries) {
        const children = categories.get(entry.houseLedgerOptionId) || [];
        children.push(entry);
        categories.set(entry.houseLedgerOptionId, children);
    }
    return [...categories.entries()].sort(([a], [b]) => a - b).map(([id, children]) => ({
        id, entries: children, type: children[0].txType, totals: ledgerTotals(children, currency),
    }));
}

export function ledgerBalanceClass(balance: number, missing = false): string {
    if (missing || balance === 0) return 'ledger-balance';
    return balance > 0 ? 'ledger-income' : 'ledger-expense';
}
