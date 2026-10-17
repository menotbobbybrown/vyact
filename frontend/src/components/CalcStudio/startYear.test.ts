import {afterEach, describe, expect, it, vi} from 'vitest';
import {calculateProjection, createEmptyProjection, emptyProjection, loadProjection, PROJECTION_STORAGE_KEY} from './projection';
const base = {...emptyProjection, initialAmount: '1000', annualReturn: '0', investmentYears: '3', startYear: '2026'};
afterEach(() => {vi.unstubAllGlobals(); vi.useRealTimers();});

describe('saved calendar year', () => {
    it('uses the selected calendar year as the first projection year', () => {
        expect(calculateProjection(base).map(row => row.calendarYear)).toEqual([2026, 2027, 2028]);
    });
    it('defaults a new or legacy plan to the current year', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-10-17T12:00:00Z'));
        expect(createEmptyProjection().startYear).toBe('2026');
        vi.stubGlobal('localStorage', {getItem: () => JSON.stringify({...base, startYear: undefined})});
        expect(loadProjection().startYear).toBe('2026');
    });
    it('restores saved identity and years even after the calendar changes', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2027-10-17T12:00:00Z'));
        const saved = {...base, profileName: 'Alex', currentAge: '35', endAge: '90', withdrawalAge: '65'};
        vi.stubGlobal('localStorage', {getItem: (key: string) => key === PROJECTION_STORAGE_KEY ? JSON.stringify(saved) : null});
        expect(loadProjection()).toEqual({...saved, birthYear: '1990'});
        const rows = calculateProjection(loadProjection());
        expect(rows[0].calendarYear).toBe(2026);
        expect(rows[54].calendarYear).toBe(2080);
        expect(rows[54].age).toBe(90);
    });
    it('handles unavailable storage', () => {
        vi.stubGlobal('localStorage', {getItem: () => {throw new Error('unavailable');}});
        expect(loadProjection().startYear).toBe(String(new Date().getFullYear()));
    });
    it.each(['1899', '9900', '2026.5', 'invalid'])('rejects invalid year %s', startYear => {
        expect(() => calculateProjection({...base, startYear})).toThrow();
    });
});
