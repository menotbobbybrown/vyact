import {describe, expect, it} from 'vitest';
import {excludeAllPrompts, normalizeSelectedPrompts} from './promptProcessingDraft';
import {reorderPromptDraft} from './reorderPromptDraft';

const draft = [{id: 'a', enabled: true}, {id: 'b', enabled: true}, {id: 'c', enabled: true}, {id: 'd', enabled: false}];
describe('prompt drag ordering', () => {
    it('moves the first item to the second position', () => {
        expect(reorderPromptDraft(draft, 'a', true, 'b').map(item => item.id)).toEqual(['b', 'a', 'c', 'd']);
        expect(draft.map(item => item.id)).toEqual(['a', 'b', 'c', 'd']);
    });
    it('moves upward to the target position', () => {
        expect(reorderPromptDraft(draft, 'c', true, 'a').map(item => item.id)).toEqual(['c', 'a', 'b', 'd']);
    });
    it('inserts an excluded item before a target in the included list', () => {
        const result = reorderPromptDraft(draft, 'd', true, 'b');
        expect(result.map(item => item.id)).toEqual(['a', 'd', 'b', 'c']);
        expect(result[1].enabled).toBe(true);
    });
    it('appends to an empty excluded list and leaves self-drops unchanged', () => {
        expect(reorderPromptDraft(draft.slice(0, 3), 'a', false)[0]).toEqual({id: 'a', enabled: false});
        expect(reorderPromptDraft(draft, 'a', true, 'a')).toBe(draft);
    });
});

describe('request-selected prompts', () => {
    const selected = ['selectedPrompt', 'external', 'toolContext', 'mcp', 'folders'].map(id => ({id, enabled: true}));
    it('keeps selections included on bulk exclusion and restores legacy exclusions', () => {
        expect(excludeAllPrompts([...selected, ...draft]).filter(item => item.enabled)).toEqual(selected);
        expect(normalizeSelectedPrompts(selected.map(item => ({...item, enabled: false})))).toEqual(selected);
    });
    it('blocks dragging selections out while allowing reordering', () => {
        expect(reorderPromptDraft(selected, 'selectedPrompt', false)).toBe(selected);
        expect(reorderPromptDraft(selected, 'selectedPrompt', true, 'external')[1].id).toBe('selectedPrompt');
    });
});

it('appends arrow-included items after all included items regardless of their old position', () => {
    const items = [
        {id: 'selectedPrompt', enabled: true},
        {id: 'date', enabled: false},
        {id: 'external', enabled: true},
        {id: 'toolContext', enabled: true},
        {id: 'mcp', enabled: true},
    ];
    const result = reorderPromptDraft(items, 'date', true);
    expect(result.filter(item => item.enabled).map(item => item.id))
        .toEqual(['selectedPrompt', 'external', 'toolContext', 'mcp', 'date']);
    expect(reorderPromptDraft(items, 'date', true, 'toolContext').map(item => item.id))
        .toEqual(['selectedPrompt', 'external', 'date', 'toolContext', 'mcp']);
});
