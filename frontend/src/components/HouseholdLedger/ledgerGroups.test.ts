import {describe, expect, it} from 'vitest';
import {categoryGroups, convertedAmount, groupEntries, ledgerTotals} from './ledgerGroups';
import type {LedgerEntry} from '../../services/vyvow';

const entry = (id: number, createdAt: string): LedgerEntry => ({id, createdAt, txType: 'EXPENSE', houseLedgerOptionId: 1, memberBoardFileId: 0, currency: 'USD', amount: 10, memo: '', tag: ''});
describe('ledger grouping and currency totals', () => {
    it('sorts same-day entries newest first and groups weeks across month boundaries', () => {
        const rows = [entry(1, '2026-10-01'), entry(3, '2026-10-01'), entry(2, '2026-10-05')];
        expect(groupEntries(rows, 'daily')[1][1].map(row => row.id)).toEqual([3, 1]);
        expect(groupEntries(rows, 'weekly').map(([key]) => key)).toEqual(['2026-10-05', '2026-09-28']);
        expect(groupEntries(rows, 'monthly')).toHaveLength(1);
    });
    it('uses historical conversion rates and never sums incompatible currencies', () => {
        expect(convertedAmount(entry(1, '2026-10-01'), 'USD')).toBe(10);
        expect(convertedAmount(entry(1, '2026-10-01'), 'KRW')).toBeNull();
        expect(convertedAmount({...entry(1, '2026-10-01'), rate: 1, targetRate: 1350}, 'KRW')).toBe(13500);
    });
});

describe('category aggregation', () => {
    it('aggregates categories in each period and keeps children newest first', () => {
        const rows = [entry(1, '2026-10-12'), {...entry(4, '2026-10-17'), currency: 'KRW', amount: 1000},
            {...entry(5, '2026-10-16'), houseLedgerOptionId: 5}, entry(3, '2026-10-12')];
        const week = groupEntries(rows, 'weekly')[0][1];
        const categories = categoryGroups(week, 'KRW');
        expect(categories.map(category => category.id)).toEqual([1, 5]);
        expect(categories[0].entries.map(row => row.id)).toEqual([4, 3, 1]);
        expect(categories[0].totals.expense).toBe(1000);
        expect(categories[0].totals.missing).toBe(true);
        expect(categoryGroups(groupEntries(rows, 'monthly')[0][1], 'USD')[0].entries).toHaveLength(3);
    });
    it('separates income, expense and net using historical exchange rates', () => {
        const rows = [{...entry(1, '2026-10-01'), rate: 1, targetRate: 1350},
            {...entry(2, '2026-10-01'), txType: 'INCOME' as const, currency: 'KRW', amount: 20000}];
        expect(ledgerTotals(rows, 'KRW')).toEqual({income: 20000, expense: 13500, balance: 6500, missing: false});
    });
});
