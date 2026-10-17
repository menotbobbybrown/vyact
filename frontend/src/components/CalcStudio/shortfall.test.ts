import {describe, expect, it} from 'vitest';
import {calculateProjection, emptyProjection, summarizeProjection} from './projection';
const plan = {...emptyProjection, startYear: '2026', birthYear: '1983', endAge: '100', initialAmount: '100000000', annualContribution: '20000000', contributionYears: '3', annualWithdrawal: '20000000', withdrawalAge: '50', annualReturn: '10', inflationRate: '3'};
describe('asset depletion and withdrawal shortfalls', () => {
    it('reproduces the reported plan without fictitious debt or negative returns', () => {
        const rows = calculateProjection(plan);
        const summary = summarizeProjection(rows);
        expect(summary.depleted).toMatchObject({calendarYear: 2068, age: 85});
        const depleted = rows.find(row => row.calendarYear === 2068)!;
        expect(depleted.withdrawal).toBeCloseTo(13_881_416.81, 2);
        expect(depleted.shortfall).toBeCloseTo(44_084_149.75, 2);
        expect(depleted.interest).toBe(0);
        expect(rows.every(row => row.balance >= 0 && row.interest >= 0)).toBe(true);
        expect(rows[rows.length - 1].balance).toBe(0);
        expect(summary.shortfall).toBeGreaterThan(0);
        for (const row of rows) expect(row.withdrawal + row.shortfall).toBeCloseTo(row.plannedWithdrawal);
        expect(100_000_000 + 60_000_000 + summary.interest - summary.withdrawal).toBeCloseTo(0, 4);
    });
    it('tracks unpaid withdrawals separately while later contributions can restore assets', () => {
        const rows = calculateProjection({...emptyProjection, initialAmount: '0', annualReturn: '10', investmentYears: '3', annualWithdrawal: '100', withdrawalStartYear: '2', annualContribution: '200', contributionYears: '1'});
        expect(rows[1]).toMatchObject({withdrawal: 0, shortfall: 100, interest: 20, balance: 220});
        expect(rows[2]).toMatchObject({withdrawal: 100, shortfall: 0, interest: 12, balance: 132});
    });
    it('retains actual investment losses when the return assumption is negative', () => {
        const rows = calculateProjection({...emptyProjection, initialAmount: '100', annualReturn: '-100', investmentYears: '2'});
        expect(rows[0]).toMatchObject({interest: -100, balance: 0, shortfall: 0});
        expect(rows[1].interest).toBe(0);
    });
});
