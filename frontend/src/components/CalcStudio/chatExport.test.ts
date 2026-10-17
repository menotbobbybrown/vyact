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
        expect(text).toContain('| 1 | 2026 | 1000 | 0 | 100 | 0 | 0 | 1100 |');
        expect(text).toContain('| 3 | 2028 | 1320 | 0 | 132 | 0 | 0 | 1452 |');
        expect(inputs.initialAmount).toBe('1000');
    });
});
