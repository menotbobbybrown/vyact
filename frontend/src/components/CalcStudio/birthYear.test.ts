import {describe, expect, it} from 'vitest';
import {calculateProjection, emptyProjection} from './projection';
const plan = {...emptyProjection, birthYear: '1990', startYear: '2026', endAge: '90', initialAmount: '1000', annualReturn: '0'};
describe('birth year planning', () => {
    it('matches each year-end age to the calendar year and includes the end age', () => {
        const rows = calculateProjection(plan);
        expect(rows).toHaveLength(55);
        expect(rows[0]).toMatchObject({calendarYear: 2026, age: 36});
        expect(rows[54]).toMatchObject({calendarYear: 2080, age: 90});
        expect(rows.every(row => row.age === row.calendarYear - 1990)).toBe(true);
    });
    it('allows age 200 and withdrawals beyond the former 100-year limit', () => {
        const rows = calculateProjection({...plan, birthYear: '1983', endAge: '200', withdrawalAge: '180', annualWithdrawal: '1'});
        expect(rows).toHaveLength(158);
        expect(rows[157].age).toBe(200);
        expect(rows.find(row => row.age === 180)?.withdrawal).toBe(1);
    });
    it('allows the starting age as end age for a single year', () => {
        expect(calculateProjection({...plan, endAge: '36'})).toHaveLength(1);
        expect(() => calculateProjection({...plan, endAge: '35'})).toThrow();
    });
    it('starts withdrawals at the selected age', () => {
        const rows = calculateProjection({...plan, withdrawalAge: '65', annualWithdrawal: '10'});
        expect(rows.find(row => row.age === 64)?.withdrawal).toBe(0);
        expect(rows.find(row => row.age === 65)?.withdrawal).toBe(10);
    });
    it.each(['2027', '1990.5', '-1'])('rejects invalid birth year %s', birthYear => {
        expect(() => calculateProjection({...plan, birthYear})).toThrow();
    });
});
