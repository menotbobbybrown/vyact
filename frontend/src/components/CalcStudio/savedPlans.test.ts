import {afterEach, expect, it, vi} from 'vitest';
import {deletePlan, listSavedPlans, savePlan} from './savedPlans';
import {emptyProjection} from './projection';
afterEach(() => vi.unstubAllGlobals());
it('creates, overwrites, lists and deletes named plans without changing the local cache', async () => {
    const plan = {id: 'plan-id', name: 'Base', inputs: emptyProjection, profileNameOverridden: true};
    const fetchMock = vi.fn().mockResolvedValue({ok: true, json: async () => ({plan, plans: [plan]})});
    vi.stubGlobal('fetch', fetchMock);
    expect(await savePlan('Base', emptyProjection, true)).toEqual(plan);
    expect(fetchMock.mock.calls[0][1].method).toBe('POST');
    await savePlan('Base', emptyProjection, true, plan.id);
    expect(fetchMock.mock.calls[1][0]).toBe('/api/wealth-lab/plans/plan-id');
    expect(fetchMock.mock.calls[1][1].method).toBe('PUT');
    expect(await listSavedPlans()).toEqual([plan]);
    await deletePlan(plan.id);
    expect(fetchMock.mock.calls[3][1].method).toBe('DELETE');
});
it('rejects failed requests', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok: false}));
    await expect(listSavedPlans()).rejects.toThrow();
});
