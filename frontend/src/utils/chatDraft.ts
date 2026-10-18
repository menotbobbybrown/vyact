export const CHAT_DRAFT_EVENT = 'vyact:chat-draft';

export interface ChatDraft {
    text: string;
    title: string;
}

export function addToChat(draft: ChatDraft) {
    window.dispatchEvent(new CustomEvent<ChatDraft>(CHAT_DRAFT_EVENT, {detail: draft}));
}
