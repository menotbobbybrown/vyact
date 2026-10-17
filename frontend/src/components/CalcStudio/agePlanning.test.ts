import {describe, expect, it} from 'vitest';
import {createInstance} from 'i18next';
import en from '../../i18n/locales/en/main.json';
import {calculateProjection, emptyProjection, resolveProjectionInputs} from './projection';
import {exportProjectionToChat} from './chatExport';
const plan = {...emptyProjection, startYear: '2026', profileName: 'Alex', currentAge: '35', endAge: '90', initialAmount: '1000', annualReturn: '0'};

describe('age based planning', () => {
    it('derives the horizon and labels ages at year end through the end age', () => {
        const rows = calculateProjection(plan);
        expect(rows).toHaveLength(55);
        expect(rows[0].age).toBe(36);
        expect(rows[54].age).toBe(90);
    });
    it('derives withdrawals from age and ignores the old duration', () => {
        const values = {...plan, investmentYears: '10', withdrawalAge: '65', annualWithdrawal: '10'};
        expect(resolveProjectionInputs(values).withdrawalStartYear).toBe('30');
        const rows = calculateProjection(values);
        expect(rows[28].withdrawal).toBe(0);
        expect(rows[29].age).toBe(65);
        expect(rows[29].withdrawal).toBe(10);
        expect(rows).toHaveLength(55);
    });
    it.each([{endAge: '35'}, {currentAge: '35.5'}, {endAge: ''}, {currentAge: ''}, {withdrawalAge: '36'}, {withdrawalAge: '91'}])('rejects invalid ages %o', invalid => {
        expect(() => calculateProjection({...plan, ...invalid})).toThrow();
    });
    it('includes identity, ages, derived duration and age column in chat', async () => {
        const i18n = createInstance();
        await i18n.init({lng: 'en', defaultNS: 'main', resources: {en: {main: en}}});
        const text = exportProjectionToChat(plan, i18n.getFixedT('en', 'main'));
        expect(text).toContain('Alex');
        expect(text).toContain('Current age: 35');
        expect(text).toContain('Planning end age: 90');
        expect(text).toContain('Duration (years): 55');
        expect(text).toContain('| 1 | 2026 | 36 |');
    });
});
