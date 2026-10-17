import {describe, expect, it} from 'vitest';
import {formatProjectionAmount} from './resultFormat';
describe('localized result amounts', () => {
    it('uses Korean hundred-million units for both positive and negative amounts', () => {
        expect(formatProjectionAmount(160_000_000, 'ko')).toBe('1.6억');
        expect(formatProjectionAmount(-2_660_011_608.1, 'ko-KR')).toBe('-26.6억');
        expect(formatProjectionAmount(10_000_000, 'ko')).toBe('10,000,000');
        expect(formatProjectionAmount(100_000_000, 'ko')).toBe('1억');
    });
    it('truncates regular amounts and keeps negative compact amounts', () => {
        expect(formatProjectionAmount(20_797_213.54, 'ko')).toBe('20,797,213');
        expect(formatProjectionAmount(-44_084_149.75, 'ko')).toBe('-44,084,149');
        expect(formatProjectionAmount(-108_197_098.3, 'ko')).toBe('-1.08억');
        expect(formatProjectionAmount(-0.8, 'ko')).toBe('0');
    });
    it('uses local compact units and preserves smaller amounts', () => {
        expect(formatProjectionAmount(1_600_000, 'en')).toBe('1.6M');
        expect(formatProjectionAmount(1_000, 'en')).toBe('1,000');
        expect(formatProjectionAmount(10_000, 'ja')).toBe('1万');
        expect(formatProjectionAmount(10_000, 'zh')).toBe('1万');
    });
    it.each(['ko', 'en', 'ja', 'zh', 'th', 'vi', 'es', 'fr'])('formats signed results in %s', language => {
        expect(formatProjectionAmount(-1_234_567_890, language)).toContain('-');
        expect(formatProjectionAmount(0, language)).toBe('0');
    });
});
