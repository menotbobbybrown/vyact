import {describe, expect, it} from 'vitest';
import type {Message} from '../../types';
import {getUnansweredQuestionIndex, isUnansweredResponse, markResponseStopped, prepareRetryTurn, removeRetryTurn} from './chatRetry';

describe('stopped response retry', () => {
    it('keeps an empty response available for retry without marking it as an error', () => {
        const stopped = markResponseStopped({id: 'response', role: 'assistant', content: ''});
        expect(stopped).toMatchObject({id: 'response', content: '', isStopped: true, isError: false});
    });
    it('preserves partial output and completes pending tool activity', () => {
        const message: Message = {role: 'assistant', content: 'Partial answer', toolStatus: {phase: 'running', label: 'Search'}, activityLog: [{phase: 'running', label: 'Search'}]};
        const stopped = markResponseStopped(message);
        expect(stopped.content).toBe('Partial answer');
        expect(stopped.toolStatus).toBeUndefined();
        expect(stopped.activityLog?.[0].phase).toBe('completed');
        expect(message.activityLog?.[0].phase).toBe('running');
    });
    it.each(['isStopped', 'isError'] as const)('removes only the retried turn for %s', flag => {
        const earlier: Message = {role: 'assistant', content: 'Earlier answer'};
        const messages: Message[] = [earlier, {role: 'user', content: 'Question', attachments: [{type: 'file', filename: 'test.txt'}]}, {role: 'assistant', content: 'Partial', [flag]: true}];
        expect(removeRetryTurn(messages)).toEqual([earlier]);
        expect(messages).toHaveLength(3);
    });
});

describe('retry from reloaded history', () => {
    const question: Message = {role: 'user', content: 'Hi', timestamp: 'saved-time'};
    it('offers retry when only the last question was saved', () => {
        expect(getUnansweredQuestionIndex([question])).toBe(0);
        expect(removeRetryTurn([question])).toEqual([]);
    });
    it.each([
        {role: 'assistant', content: ''},
        {role: 'assistant', content: 'No response', isError: true, errorCode: 'model_no_response'},
    ] as Message[])('hides empty legacy response and retries its question', response => {
        expect(isUnansweredResponse(response)).toBe(true);
        expect(getUnansweredQuestionIndex([question, response])).toBe(0);
        expect(removeRetryTurn([question, response])).toEqual([]);
    });
    it('does not offer retry for completed or partially answered questions', () => {
        for (const response of [
            {role: 'assistant', content: 'Answer'},
            {role: 'assistant', content: 'Partial', isStopped: true},
            {role: 'assistant', content: '', attachments: [{type: 'image', filename: 'image.png'}]},
            {role: 'assistant', content: 'Tool failed', errorCode: 'tool_call_failed', isError: true},
        ] as Message[]) {
            expect(getUnansweredQuestionIndex([question, response])).toBe(-1);
            expect(isUnansweredResponse(response)).toBe(false);
        }
    });
    it('targets only the latest unanswered question', () => {
        expect(getUnansweredQuestionIndex([question, {role: 'assistant', content: ''}, {...question, content: 'Next'}])).toBe(2);
        expect(getUnansweredQuestionIndex([])).toBe(-1);
    });
});

it('repeated retry and stop preserve one original question in UI and saved history', () => {
    const earlier: Message[] = [{role: 'user', content: 'Earlier'}, {role: 'assistant', content: 'Answer'}];
    const question: Message = {id: 'original', role: 'user', content: 'Retry me', timestamp: 'original-time', attachments: [{type: 'file', filename: 'test.txt'}]};
    let visible: Message[] = [...earlier, question, {role: 'assistant', content: '', isStopped: true}];
    for (let attempt = 0; attempt < 3; attempt++) {
        const originalState = [...visible];
        const retry = prepareRetryTurn(visible, question);
        expect(visible).toEqual(originalState);
        expect(retry.history).toEqual(earlier);
        expect(retry.userMessage).toBe(question);
        // Both the immediate UI and the server save use the same explicit snapshot.
        const sentHistory = [...retry.history, retry.userMessage];
        visible = [...retry.history, retry.userMessage, {role: 'assistant', content: '', isStopped: true}];
        expect(visible.filter(message => message.role === 'user')).toEqual(sentHistory.filter(message => message.role === 'user'));
        expect(sentHistory.filter(message => message.content === 'Retry me')).toHaveLength(1);
        expect(sentHistory[sentHistory.length - 1].timestamp).toBe('original-time');
        // Reopening history removes only the empty response placeholder.
        if (attempt === 1) visible = sentHistory;
    }
});
