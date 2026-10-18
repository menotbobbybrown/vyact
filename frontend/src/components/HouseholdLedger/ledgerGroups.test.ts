import {describe, expect, it} from 'vitest';
import {convertedAmount, groupEntries} from './ledgerGroups';
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
