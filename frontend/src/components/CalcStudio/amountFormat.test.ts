import {describe, expect, it} from 'vitest';
import {formatAmountInput, parseAmountInput} from './amountFormat';

describe('localized amount input', () => {
    it('groups Korean amounts without changing calculation values', () => {
        expect(formatAmountInput('10000000', 'ko')).toBe('10,000,000');
        expect(parseAmountInput('10,000,000', 'ko')).toBe('10000000');
    });
    it('preserves incomplete decimals and empty input', () => {
        expect(formatAmountInput('1000.', 'en')).toBe('1,000.');
        expect(formatAmountInput('1000.050', 'en')).toBe('1,000.050');
        expect(formatAmountInput('', 'ko')).toBe('');
        expect(parseAmountInput('', 'ko')).toBe('');
    });
    it.each(['ko', 'en', 'ja', 'zh', 'th', 'vi', 'es', 'fr'])('round trips decimal amounts in %s', language => {
        expect(parseAmountInput(formatAmountInput('1234567.89', language), language)).toBe('1234567.89');
    });
    it('does not round large integer inputs', () => {
        expect(formatAmountInput('9007199254740993', 'en')).toBe('9,007,199,254,740,993');
    });
    it('rejects invalid and negative amounts', () => {
        expect(parseAmountInput('abc', 'ko')).toBeNull();
        expect(parseAmountInput('-100', 'ko')).toBeNull();
        expect(parseAmountInput('1.2.3', 'en')).toBeNull();
    });
});
