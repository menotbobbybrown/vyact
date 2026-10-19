import {afterEach, describe, expect, it, vi} from 'vitest';
import {calculateProjection, emptyProjection, getIncomeSources, loadProjection, withIncomeSources, type IncomeSource} from './projection';
const base = {...emptyProjection, initialAmount: '100000', annualReturn: '0', currentAge: '49', endAge: '65', inflationRate: '3'};
const source = (id: string, startAge: string, monthlyAmount = '100', endAge = ''): IncomeSource => ({id, name: id, monthlyAmount, startAge, endAge});
afterEach(() => vi.unstubAllGlobals());
describe('multiple income sources', () => {
    it('combines independently timed and inflated income streams', () => {
        const rows = calculateProjection({...base, incomeSources: [source('pension', '50'), source('private', '52', '200', '53')]});
        expect(rows[0].income).toBe(1200);
        expect(rows[2].income).toBeCloseTo(3600 * 1.03 ** 2);
        expect(rows[3].income).toBeCloseTo(3600 * 1.03 ** 3);
        expect(rows[4].income).toBeCloseTo(1200 * 1.03 ** 4);
    });
    it('follows the plan end when no income end is specified', () => {
        const inputs = {...base, incomeSources: [source('pension', '60')]};
        const rows = calculateProjection(inputs);
        expect(rows[rows.length - 1].income).toBeGreaterThan(0);
        const extended = calculateProjection({...inputs, endAge: '70'});
        expect(extended[extended.length - 1].income).toBeGreaterThan(0);
        expect(inputs.incomeSources[0].endAge).toBe('');
    });
    it('migrates old local conditions without counting income twice', () => {
        vi.stubGlobal('localStorage', {getItem: () => JSON.stringify({...base, monthlyIncome: '100', incomeStartAge: '60'})});
        const loaded = loadProjection();
        expect(loaded.monthlyIncome).toBe('');
        expect(getIncomeSources(loaded)).toEqual([source('legacy', '60')].map(item => ({...item, name: ''})));
        expect(calculateProjection(loaded)[10].income).toBeCloseTo(1200 * 1.03 ** 10);
        expect(withIncomeSources(loaded, []).incomeSources).toEqual([]);
    });
    it.each([source('missing', ''), source('missing-amount', '60', ''), source('reversed', '60', '100', '59'), source('late', '60', '100', '66')])('rejects incomplete or invalid income: %o', income => {
        expect(() => calculateProjection({...base, incomeSources: [income]})).toThrow();
    });
});
