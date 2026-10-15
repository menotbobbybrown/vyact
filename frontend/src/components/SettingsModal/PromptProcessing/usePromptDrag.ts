import {useState, useRef, type DragEvent} from 'react';
import {reorderPromptDraft} from './reorderPromptDraft';
import {type PromptDraft} from './promptProcessingDraft';

export function usePromptDrag(draft: PromptDraft[], onChange: (next: PromptDraft[]) => void) {
    const draggedRef = useRef<string | null>(null);
    const [draggedId, setDraggedId] = useState<string | null>(null);
    const [targetId, setTargetId] = useState<string | null>(null);
    const finish = () => {draggedRef.current = null; setDraggedId(null); setTargetId(null);};
    const canDrop = () => draft.some(item => item.id === draggedRef.current);
    const drop = (event: DragEvent, enabled: boolean, targetRowId?: string) => {
        event.preventDefault();
        event.stopPropagation();
        const item = draft.find(item => item.id === draggedRef.current);
        if (!item || !canDrop() || targetRowId === item.id) {finish(); return;}
        onChange(reorderPromptDraft(draft, item.id, enabled, targetRowId));
        finish();
    };
    return {draggedId, targetId, finish, canDrop, drop,
        start: (event: DragEvent, id: string) => {
            draggedRef.current = id;
            setDraggedId(id);
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', id);
            // Drag the complete card rather than the small handle button.
            const card = event.currentTarget.closest<HTMLElement>('.prompt-processing-item');
            if (card) {
                const bounds = card.getBoundingClientRect();
                event.dataTransfer.setDragImage(card, event.clientX - bounds.left, event.clientY - bounds.top);
            }
        },
        over: (event: DragEvent, enabled: boolean, id?: string) => {
            if (!canDrop()) return;
            event.preventDefault(); event.stopPropagation();
            event.dataTransfer.dropEffect = 'move';
            setTargetId(id ?? (enabled ? 'included' : 'excluded'));
        },
    };
}
