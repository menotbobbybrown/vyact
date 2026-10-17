import {afterEach, describe, expect, it, vi} from 'vitest';
import {loadProfileNameOverride} from './profileNamePreference';
afterEach(() => vi.unstubAllGlobals());
describe('profile name preference', () => {
    it.each([
        [{}, false],
        [{profileName: 'Alex', profileNameOverridden: false}, false],
        [{profileName: 'Other', profileNameOverridden: true}, true],
        [{profileName: '', profileNameOverridden: true}, true],
        [{profileName: 'Legacy custom name'}, true],
        [{profileName: ''}, false],
    ])('restores explicit overrides and preserves legacy custom names: %o', (saved, expected) => {
        vi.stubGlobal('localStorage', {getItem: () => JSON.stringify(saved)});
        expect(loadProfileNameOverride()).toBe(expected);
    });
    it('falls back to the profile when storage fails', () => {
        vi.stubGlobal('localStorage', {getItem: () => {throw new Error('unavailable');}});
        expect(loadProfileNameOverride()).toBe(false);
    });
});
