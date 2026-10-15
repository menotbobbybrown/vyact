import {loadPromptDraft, normalizeSelectedPrompts, type PromptDrafts} from './promptProcessingDraft';

export async function fetchPromptSettings(): Promise<{drafts: PromptDrafts; saved: PromptDrafts}> {
    const response = await fetch('/api/prompt-processing');
    if (!response.ok) throw new Error('Prompt settings load failed');
    const result = await response.json();
    const saved = {general: normalizeSelectedPrompts(result.settings.general), project: normalizeSelectedPrompts(result.settings.project)};
    const drafts = result.configured ? saved : loadPromptDraft();
    // Loading or migrating existing settings is not a user edit.
    return {drafts, saved: structuredClone(drafts)};
}

export async function persistPromptSettings(drafts: PromptDrafts): Promise<PromptDrafts> {
    const response = await fetch('/api/prompt-processing', {
        method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(drafts),
    });
    if (!response.ok) throw new Error('Prompt settings save failed');
    const saved = (await response.json()).settings;
    return saved;
}
