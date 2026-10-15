import type {PromptDraft} from './promptProcessingDraft';

/** Dropping onto a row takes its position: downward after it, upward before it. */
export function reorderPromptDraft(draft: PromptDraft[], draggedId: string, enabled: boolean, targetId?: string): PromptDraft[] {
    const item = draft.find(candidate => candidate.id === draggedId);
    if (!item || targetId === draggedId) return draft;
    const originalDestination = draft.filter(candidate => candidate.enabled === enabled);
    const targetIndex = targetId ? originalDestination.findIndex(candidate => candidate.id === targetId) : -1;
    const destination = originalDestination.filter(candidate => candidate.id !== draggedId);
    destination.splice(targetIndex < 0 ? destination.length : targetIndex, 0, {...item, enabled});
    return [...destination, ...draft.filter(candidate => candidate.id !== draggedId && candidate.enabled !== enabled)];
}
