type LabeledMail = {id: string; labelIds?: string[]};

export const isDraftMail = (mail: LabeledMail) => mail.labelIds?.includes('DRAFT') ?? false;

// Detail labels can be the union of the entire conversation. Use message labels
// whenever available, and keep the existing action target unless it is a draft.
export function getMailActionTarget<T extends LabeledMail>(messages: T[], selectedId: string): T | undefined {
    const selected = messages.find(message => message.id === selectedId);
    return selected && !isDraftMail(selected)
        ? selected
        : [...messages].reverse().find(message => !isDraftMail(message));
}
