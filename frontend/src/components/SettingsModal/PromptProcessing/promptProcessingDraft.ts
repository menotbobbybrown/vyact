import content from './defaultPromptContent.json';

export interface PromptDraft {
    id: string;
    title?: string;
    content?: string;
    enabled: boolean;
    source?: 'user';
    createdOrder?: number;
}

// UI preview only. These snapshots never participate in request construction.
export const PROMPT_DEFINITIONS = [
    {id: 'base', content: content.FORMAT_INSTRUCTION},
    {id: 'selectedPrompt'},
    {id: 'project'}, {id: 'projectMemory'}, {id: 'personalMemory', searchConditional: true}, {id: 'folders'},
    {id: 'tone'}, {id: 'metadata'}, {id: 'external'},
    {id: 'length', content: content.RESPONSE_LENGTH_INSTRUCTION},
    {id: 'reasoning', content: content.REASONING_BUDGET_INSTRUCTION},
    {id: 'date'}, {id: 'profile'}, {id: 'summary'}, {id: 'skills', searchConditional: true}, {id: 'language'},
    {id: 'tools', content: content.TOOL_INSTRUCTION}, {id: 'toolContext'}, {id: 'mcp'},
] as const;

export type PromptScope = 'general' | 'project';
export type PromptDrafts = Record<PromptScope, PromptDraft[]>;
const DRAFT_STORAGE_KEY = 'vyact-prompt-processing-preview-v2';
const LEGACY_STORAGE_KEY = 'vyact-prompt-processing-preview-v1';
export const getPromptDefinition = (id: string) => PROMPT_DEFINITIONS.find(item => item.id === id);
const belongsToScope = (id: string, scope: PromptScope) => scope === 'general'
    ? !['project', 'projectMemory'].includes(id) : id !== 'personalMemory';

export function createDefaultPromptDraft(scope: PromptScope): PromptDraft[] {
    return PROMPT_DEFINITIONS.filter(item => belongsToScope(item.id, scope))
        .map(item => ({id: item.id, enabled: true}));
}

function normalizeDraft(saved: unknown, scope: PromptScope): PromptDraft[] {
    if (!Array.isArray(saved)) return createDefaultPromptDraft(scope);
    const seen = new Set<string>();
    const restored: PromptDraft[] = [];
    for (const item of saved) {
        if (!item || typeof item.id !== 'string' || seen.has(item.id)
            || typeof item.enabled !== 'boolean'
            || (item.title !== undefined && typeof item.title !== 'string')
            || (item.content !== undefined && typeof item.content !== 'string')) continue;
        const definition = getPromptDefinition(item.id);
        if (item.source === 'user' && item.id.startsWith('custom:')) {
            restored.push({id: item.id, source: 'user', title: item.title ?? '', content: item.content ?? '', enabled: item.enabled,
                createdOrder: Number.isFinite(item.createdOrder) && item.createdOrder >= 0 ? item.createdOrder : saved.indexOf(item)});
        } else if (definition && belongsToScope(item.id, scope)) {
            restored.push('content' in definition
                ? {id: item.id, title: item.title, content: item.content, enabled: item.enabled}
                : {id: item.id, enabled: item.enabled});
        } else continue;
        seen.add(item.id);
    }
    if (!seen.has('selectedPrompt')) {
        const baseIndex = restored.findIndex(item => item.id === 'base');
        restored.splice(baseIndex < 0 ? 0 : baseIndex + 1, 0, {id: 'selectedPrompt', enabled: true});
        seen.add('selectedPrompt');
    }
    return [...restored, ...createDefaultPromptDraft(scope).filter(item => !seen.has(item.id))
        .map(item => ({...item, enabled: !('content' in getPromptDefinition(item.id)!)}))];
}

export function loadPromptDraft(): PromptDrafts {
    try {
        const saved = JSON.parse(localStorage.getItem(DRAFT_STORAGE_KEY) || 'null');
        if (saved && typeof saved === 'object' && !Array.isArray(saved)) {
            return {general: normalizeDraft(saved.general, 'general'), project: normalizeDraft(saved.project, 'project')};
        }
        const legacy = JSON.parse(localStorage.getItem(LEGACY_STORAGE_KEY) || 'null');
        return {general: normalizeDraft(legacy, 'general'), project: normalizeDraft(legacy, 'project')};
    } catch {
        return {general: createDefaultPromptDraft('general'), project: createDefaultPromptDraft('project')};
    }
}


/** Excluded prompts have a stable catalog order, independent of application order. */
export function sortExcludedPrompts(draft: PromptDraft[]): PromptDraft[] {
    const defaultOrder = new Map<string, number>(PROMPT_DEFINITIONS.map((item, index) => [item.id, index]));
    return draft.filter(item => !item.enabled).sort((left, right) => {
        const leftUser = left.source === 'user';
        const rightUser = right.source === 'user';
        if (leftUser !== rightUser) return leftUser ? 1 : -1;
        const difference = leftUser
            ? (left.createdOrder ?? 0) - (right.createdOrder ?? 0)
            : (defaultOrder.get(left.id) ?? 0) - (defaultOrder.get(right.id) ?? 0);
        return difference || left.id.localeCompare(right.id);
    });
}
