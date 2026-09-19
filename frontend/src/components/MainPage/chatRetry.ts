import type {Message} from '../../types';

export function markResponseStopped(message: Message): Message {
    return {
        ...message,
        content: message.content,
        isStopped: true,
        isError: false,
        toolStatus: undefined,
        activityLog: message.activityLog?.map(activity => activity.phase === 'completed'
            ? activity
            : {...activity, phase: 'completed', completedAt: Date.now()}),
    };
}

export function removeRetryTurn(messages: Message[]): Message[] {
    const next = [...messages];
    const last = next[next.length - 1];
    if (last?.role === 'assistant' && (last.isError || last.isStopped)) next.pop();
    if (next[next.length - 1]?.role === 'user') next.pop();
    return next;
}
