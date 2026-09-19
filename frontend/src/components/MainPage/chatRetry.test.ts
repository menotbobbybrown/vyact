import {describe, expect, it} from 'vitest';
import type {Message} from '../../types';
import {markResponseStopped, removeRetryTurn} from './chatRetry';

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
