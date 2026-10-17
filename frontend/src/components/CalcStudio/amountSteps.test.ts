import {describe, expect, it} from 'vitest';
import {getAmountSteps} from './amountSteps';

describe('localized amount shortcuts', () => {
    it('uses Korean amounts and units', () => {
        expect(getAmountSteps('ko-KR')).toEqual([
            {value: 100_000_000, label: '+1억'},
            {value: 10_000_000, label: '+1000만'},
            {value: 1_000_000, label: '+100만'},
        ]);
    });
    it('uses distinct English billion, million and thousand amounts', () => {
        expect(getAmountSteps('en')).toEqual([
            {value: 1_000_000_000, label: '+1B'},
            {value: 1_000_000, label: '+1M'},
            {value: 1_000, label: '+1K'},
        ]);
    });
    it.each(['ja', 'zh'])('uses hundred-million and ten-thousand steps for %s', language => {
        expect(getAmountSteps(language).map(step => step.value)).toEqual([100_000_000, 10_000, 1_000]);
    });
    it.each(['ko', 'en', 'ja', 'zh', 'th', 'vi', 'es', 'fr'])('has unambiguous shortcuts for %s', language => {
        const steps = getAmountSteps(language);
        expect(new Set(steps.map(step => step.label)).size).toBe(3);
        expect(steps.every(step => step.value > 0 && step.label.startsWith('+'))).toBe(true);
    });
});
