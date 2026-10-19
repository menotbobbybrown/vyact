import {afterEach, describe, expect, it, vi} from 'vitest';
import {persistProjection, restoreProjectionCache} from './projectionPersistence';
import {emptyProjection, PROJECTION_STORAGE_KEY} from './projection';

afterEach(() => vi.unstubAllGlobals());
describe('projection persistence', () => {
    it('sends the snapshot and serializes a following reset', async () => {
        const fetchMock = vi.fn().mockResolvedValue({ok: true});
        vi.stubGlobal('fetch', fetchMock);
        const snapshot = {inputs: {...emptyProjection, initialAmount: '100'}, profileNameOverridden: true};
        await Promise.all([persistProjection(snapshot), persistProjection(null)]);
        expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(snapshot);
        expect(fetchMock.mock.calls[1][1].method).toBe('DELETE');
    });
    it('restores the exact local cache shape including the name override', async () => {
        const setItem = vi.fn();
        const snapshot = {inputs: emptyProjection, profileNameOverridden: true};
        vi.stubGlobal('localStorage', {setItem});
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok: true, json: async () => ({snapshot})}));
        await restoreProjectionCache();
        expect(setItem).toHaveBeenCalledWith(PROJECTION_STORAGE_KEY, JSON.stringify({...emptyProjection, profileNameOverridden: true}));
    });
    it('preserves the local cache when an older backup has no snapshot', async () => {
        const setItem = vi.fn();
        vi.stubGlobal('localStorage', {setItem});
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok: true, json: async () => ({snapshot: null})}));
        await restoreProjectionCache();
        expect(setItem).not.toHaveBeenCalled();
    });
    it('reports failed persistence without blocking subsequent operations', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ok: false}).mockResolvedValueOnce({ok: true}));
        await expect(persistProjection(null)).rejects.toThrow();
        await expect(persistProjection(null)).resolves.toBeUndefined();
    });
});
