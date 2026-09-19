import {describe, expect, it} from 'vitest';
import type {Message} from '../../types';
import {getUnansweredQuestionIndex, isUnansweredResponse, markResponseStopped, removeRetryTurn} from './chatRetry';

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
