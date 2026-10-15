import {expect, it, vi} from 'vitest';
import {createDefaultPromptDraft, loadPromptDraft, sortExcludedPrompts, type PromptDraft} from './promptProcessingDraft';

it('keeps default items first and custom items in saved creation order after reordering', () => {
    const draft: PromptDraft[] = [
        {id: 'custom:later', source: 'user', createdOrder: 2, enabled: false},
        {id: 'date', enabled: false},
        {id: 'custom:first', source: 'user', createdOrder: 1, enabled: false},
        {id: 'base', enabled: false},
        {id: 'profile', enabled: true},
    ];
    const expected = ['base', 'date', 'custom:first', 'custom:later'];
    expect(sortExcludedPrompts(draft).map(item => item.id)).toEqual(expected);
    expect(sortExcludedPrompts([...draft].reverse()).map(item => item.id)).toEqual(expected);
    expect(sortExcludedPrompts(JSON.parse(JSON.stringify(draft))).map(item => item.id)).toEqual(expected);
});

it('migrates split rules using the existing base state without losing edits', () => {
    for (const enabled of [true, false]) {
        vi.stubGlobal('localStorage', {getItem: () => JSON.stringify({
            general: [{id: 'base', enabled, content: 'CUSTOM'}],
        })});
        try {
            const draft = loadPromptDraft().general;
            expect(draft.find(item => item.id === 'base')?.content).toBe('CUSTOM');
            expect(draft.filter(item => ['projectOutput', 'followups'].includes(item.id)))
                .toEqual([{id: 'projectOutput', enabled}, {id: 'followups', enabled}]);
        } finally {vi.unstubAllGlobals();}
    }
});

it('only shows source folders in project settings', () => {
    expect(createDefaultPromptDraft('general').some(item => item.id === 'folders')).toBe(false);
    expect(createDefaultPromptDraft('project').find(item => item.id === 'folders')?.enabled).toBe(true);
});
