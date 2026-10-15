import {afterEach, expect, it, vi} from 'vitest';
import {fetchPromptSettings} from './promptProcessingApi';
import {createDefaultPromptDraft} from './promptProcessingDraft';

afterEach(() => vi.unstubAllGlobals());

it('does not mark migrated local settings as edited on first open', async () => {
    const settings = {general: createDefaultPromptDraft('general'), project: createDefaultPromptDraft('project')};
    const legacy = {...settings, general: [...settings.general,
        {id: 'custom:existing', source: 'user', title: 'Existing', content: 'Saved locally', enabled: false}]};
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok: true, json: async () => ({configured: false, settings})}));
    vi.stubGlobal('localStorage', {getItem: () => JSON.stringify(legacy)});
    const result = await fetchPromptSettings();
    expect(result.drafts.general[result.drafts.general.length - 1]?.id).toBe('custom:existing');
    expect(JSON.stringify(result.drafts)).toBe(JSON.stringify(result.saved));
    result.drafts.general[0].enabled = false;
    expect(result.saved.general[0].enabled).toBe(true);
});

it('starts persisted settings with an identical independent baseline', async () => {
    const settings = {general: createDefaultPromptDraft('general'), project: createDefaultPromptDraft('project')};
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok: true, json: async () => ({configured: true, settings})}));
    const result = await fetchPromptSettings();
    expect(result.drafts).toEqual(result.saved);
    expect(result.drafts).not.toBe(result.saved);
});
