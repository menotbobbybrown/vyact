import {describe, expect, it} from 'vitest';
import {getMailActionTarget, isDraftMail} from './mailDraftUtils';

describe('draft conversation actions', () => {
    const received = {id: 'received', labelIds: ['INBOX']};
    const sent = {id: 'sent', labelIds: ['SENT']};
    const draft = {id: 'draft', labelIds: ['DRAFT']};
    it('keeps the selected received message when the thread also contains a draft', () => {
        expect(getMailActionTarget([received, draft], received.id)).toBe(received);
    });
    it('uses the latest non-draft when opening a draft in a conversation', () => {
        expect(getMailActionTarget([received, sent, draft], draft.id)).toBe(sent);
    });
    it('disables actions for a standalone draft', () => {
        expect(getMailActionTarget([draft], draft.id)).toBeUndefined();
    });
    it('preserves normal mail behavior with absent labels', () => {
        const mail = {id: 'legacy'};
        expect(isDraftMail(mail)).toBe(false);
        expect(getMailActionTarget([mail], mail.id)).toBe(mail);
    });
});
