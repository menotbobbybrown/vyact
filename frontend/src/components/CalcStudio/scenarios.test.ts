import {describe, expect, it} from 'vitest';
import {calculateProjection, calculateScenarios, emptyProjection} from './projection';
const base = {...emptyProjection, initialAmount: '100000', annualReturn: '0', investmentYears: '12', currentAge: '49', endAge: '61', inflationRate: '3'};
describe('income and comparison scenarios', () => {
    it('inflates income during the wait and after payments start', () => {
        const rows = calculateProjection({...base, monthlyIncome: '100', incomeStartAge: '60'});
        expect(rows[9].income).toBe(0);
        expect(rows[10].income).toBeCloseTo(1200 * 1.03 ** 10);
        expect(rows[11].income).toBeCloseTo(rows[10].income * 1.03);
    });
    it('offsets expenses without investing surplus income', () => {
        const rows = calculateProjection({...base, annualWithdrawal: '100', withdrawalAge: '51', monthlyIncome: '100', incomeStartAge: '50'});
        expect(rows[0].balance).toBe(100000);
        expect(rows[1].plannedWithdrawal).toBe(0);
        expect(rows[1].balance).toBe(100000);
        expect(rows[1].presentValue).toBeCloseTo(100000 / 1.03 ** 2);
    });
    it('reports unfunded expenses after income', () => {
        const rows = calculateProjection({...base, initialAmount: '10', inflationRate: '0', annualWithdrawal: '2000', withdrawalAge: '51', monthlyIncome: '100', incomeStartAge: '51'});
        expect(rows[1].plannedWithdrawal).toBe(800);
        expect(rows[1].withdrawal).toBe(10);
        expect(rows[1].shortfall).toBe(790);
    });
    it('calculates independent, deduplicated scenarios', () => {
        const scenarios = calculateScenarios({...base, comparisonReturn1: '10', comparisonReturn2: '0.0'});
        expect(scenarios.map(scenario => scenario.annualReturn)).toEqual([0, 10]);
        expect(scenarios[0].rows[11].balance).toBe(100000);
        expect(scenarios[1].rows[11].balance).toBeCloseTo(100000 * 1.1 ** 12);
    });
    it.each([{monthlyIncome: '100'}, {monthlyIncome: '-1'}, {monthlyIncome: '100', incomeStartAge: '62'}, {comparisonReturn1: '-101'}, {comparisonReturn2: 'NaN'}])('rejects invalid optional conditions: %o', fields => {
        expect(() => calculateScenarios({...base, ...fields})).toThrow();
    });
});
