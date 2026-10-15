import {expect, it} from 'vitest';
import {sortExcludedPrompts, type PromptDraft} from './promptProcessingDraft';

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
