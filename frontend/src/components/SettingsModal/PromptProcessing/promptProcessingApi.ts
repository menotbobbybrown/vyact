import {loadPromptDraft, type PromptDrafts} from './promptProcessingDraft';

export async function fetchPromptSettings(): Promise<{drafts: PromptDrafts; saved: PromptDrafts}> {
    const response = await fetch('/api/prompt-processing');
    if (!response.ok) throw new Error('Prompt settings load failed');
    const result = await response.json();
    return {drafts: result.configured ? result.settings : loadPromptDraft(), saved: result.settings};
}

export async function persistPromptSettings(drafts: PromptDrafts): Promise<PromptDrafts> {
    const response = await fetch('/api/prompt-processing', {
        method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(drafts),
    });
    if (!response.ok) throw new Error('Prompt settings save failed');
    const saved = (await response.json()).settings;
    return saved;
}
