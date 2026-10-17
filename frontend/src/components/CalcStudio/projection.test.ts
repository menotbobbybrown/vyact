import {describe, expect, it} from 'vitest';
import {calculateProjection, emptyProjection} from './projection';
const base = {...emptyProjection, initialAmount: '1000', annualReturn: '10', investmentYears: '3'};
describe('Calc Studio projection', () => {
    it('compounds annually with contributions from year two', () => {
        const rows = calculateProjection({...base, annualContribution: '100', contributionYears: '1'});
        expect(rows.map(row => row.contribution)).toEqual([0, 100, 0]);
        expect(rows.map(row => row.balance)).toEqual([1100, 1320, 1452]);
        expect(rows[2].principal).toBe(1100);
    });
    it('inflates withdrawals before returns, matching Vyvow', () => {
        const rows = calculateProjection({...base, annualWithdrawal: '100', withdrawalStartYear: '2', inflationRate: '10'});
        expect(rows[0].withdrawal).toBe(0);
        expect(rows[1].withdrawal).toBeCloseTo(110);
        expect(rows[1].balance).toBeCloseTo(1089);
        expect(rows[2].withdrawal).toBeCloseTo(121);
        expect(rows[2].balance).toBeCloseTo(1064.8);
    });
    it('supports losses without creating fictional debt', () => {
        expect(calculateProjection({...base, annualReturn: '-100'})[0].balance).toBe(0);
        expect(calculateProjection({...base, initialAmount: '0', annualWithdrawal: '100', withdrawalStartYear: '2'})[1].balance).toBe(0);
    });
    it.each([{withdrawalStartYear: '1'}, {withdrawalStartYear: '0'},  {investmentYears: '1.5'}, {annualReturn: 'NaN'}, {initialAmount: '-1'}, {annualReturn: '-101'}, {initialAmount: '1e308', annualReturn: '1000'}, {annualWithdrawal: '100'}, {annualContribution: '100'}])('rejects invalid inputs: %o', invalid => {
        expect(() => calculateProjection({...base, ...invalid})).toThrow();
    });
});
