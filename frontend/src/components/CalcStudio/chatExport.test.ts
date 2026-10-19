import {describe, expect, it} from 'vitest';
import {createInstance} from 'i18next';
import en from '../../i18n/locales/en/main.json';
import {exportProjectionToChat} from './chatExport';
import {emptyProjection} from './projection';

describe('Wealth Lab chat export', () => {
    it('exports conditions, calculation timing, totals and every year', async () => {
        const i18n = createInstance();
        await i18n.init({lng: 'en', defaultNS: 'main', resources: {en: {main: en}}});
        const inputs = {...emptyProjection, startYear: '2026', initialAmount: '1000', annualReturn: '10', investmentYears: '3', annualContribution: '100', contributionYears: '1'};
        const text = exportProjectionToChat(inputs, i18n.getFixedT('en', 'main'));
        expect(text).toContain('## Wealth Lab');
        expect(text).not.toContain(en.calcStudio.totalShortfall);
        expect(text).not.toContain(en.calcStudio.yearlyShortfall);
        expect(text).not.toContain(en.calcStudio.fundedThroughEnd);
        expect(text).toContain('Initial capital: 1000');
        expect(text).toContain(en.calcStudio.timing);
        expect(text).toContain('Final balance: 1452');
        expect(text).toContain('Total contributions: 1100');
        expect(text).toContain('| 1 | 2026 | 1000 | 0 | 100 | 0 | 1100 |');
        expect(text).toContain('| 3 | 2028 | 1320 | 0 | 132 | 0 | 1452 |');
        expect(inputs.initialAmount).toBe('1000');
    });
    it('includes separate totals and every yearly row for all comparison returns', async () => {
        const i18n = createInstance();
        await i18n.init({lng: 'en', defaultNS: 'main', resources: {en: {main: en}}});
        const text = exportProjectionToChat({...emptyProjection, startYear: '2026', initialAmount: '1000', annualReturn: '10', comparisonReturn1: '0', comparisonReturn2: '-100', investmentYears: '2'}, i18n.getFixedT('en', 'main'));
        expect(text).toContain('### Annual return (%): 10%');
        expect(text).toContain('### Annual return (%): 0%');
        expect(text).toContain('### Annual return (%): -100%');
        expect(text).toContain('Total earnings: 210');
        expect(text).toContain('Total earnings: -1000');
        expect(text).toContain('| 2 | 2027 | 1100 | 0 | 110 | 0 | 1210 |');
        expect(text).toContain('| 2 | 2027 | 1000 | 0 | 0 | 0 | 1000 |');
        expect(text).toContain('| 2 | 2027 | 0 | 0 | 0 | 0 | 0 |');
    });

    it('exports each income source with its own amount and receipt period', async () => {
        const i18n = createInstance();
        await i18n.init({lng: 'en', defaultNS: 'main', resources: {en: {main: en}}});
        const text = exportProjectionToChat({...emptyProjection, currentAge: '49', endAge: '65', initialAmount: '10000', annualReturn: '0', incomeSources: [
            {id: 'a', name: 'Pension', monthlyAmount: '100', startAge: '60', endAge: ''},
            {id: 'b', name: 'Private', monthlyAmount: '200', startAge: '50', endAge: '59'},
        ]}, i18n.getFixedT('en', 'main'));
        expect(text).toContain('Income 1 (Pension): Monthly income (present value): 100; Income start age: 60; Income end age: 65');
        expect(text).toContain('Income 2 (Private): Monthly income (present value): 200; Income start age: 50; Income end age: 59');
        expect(text).toContain('Regular income');
    });

});
