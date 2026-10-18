import {describe, expect, it} from 'vitest';
import {calculateReturn, calculateTripDays, calculateArrival} from './calculations';

describe('return calculations', () => {
    it('calculates gains, losses and a complete loss', () => {
        expect(calculateReturn('100', '125')).toBe(25);
        expect(calculateReturn('100', '50')).toBe(-50);
        expect(calculateReturn('100', '0', '2')).toBe(-100);
    });
    it('uses compound annual growth', () => {
        expect(calculateReturn('100', '121', '2')).toBeCloseTo(10);
        expect(calculateReturn('100', '110', '0.5')).toBeCloseTo(21);
    });
    it('rejects missing, invalid and overflowing inputs', () => {
        expect(calculateReturn('', '100')).toBeNull();
        expect(calculateReturn('0', '100')).toBeNull();
        expect(calculateReturn('100', '-1')).toBeNull();
        expect(calculateReturn('100', '110', '0')).toBeNull();
        expect(calculateReturn('100', 'Infinity')).toBeNull();
    });
});
describe('travel date calculations', () => {
    it('includes or excludes departure day', () => {
        expect(calculateTripDays('2026-10-18', '2026-10-18', true)).toBe(1);
        expect(calculateTripDays('2026-10-18', '2026-10-18', false)).toBe(0);
    });
    it('handles leap days and year boundaries', () => {
        expect(calculateTripDays('2024-02-28', '2024-03-01', false)).toBe(2);
        expect(calculateArrival('2026-12-31', '2', true)).toBe(Date.parse('2027-01-01'));
        expect(calculateArrival('2026-12-31', '2', false)).toBe(Date.parse('2027-01-02'));
    });
    it('rejects reversed dates and invalid durations', () => {
        expect(calculateTripDays('2026-10-19', '2026-10-18', true)).toBeNull();
        expect(calculateArrival('', '2', true)).toBeNull();
        expect(calculateArrival('2026-10-18', '0', true)).toBeNull();
        expect(calculateArrival('2026-10-18', '1.5', true)).toBeNull();
    });
});
