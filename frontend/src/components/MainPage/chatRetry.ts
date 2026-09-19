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
    while (next.length && isUnansweredResponse(next[next.length - 1])) next.pop();
    const last = next[next.length - 1];
    if (last?.role === 'assistant' && (last.isError || last.isStopped)) next.pop();
    if (next[next.length - 1]?.role === 'user') next.pop();
    return next;
}

export function isUnansweredResponse(message: Message): boolean {
    return message.role === 'assistant'
        && !message.attachments?.length && !message.pdfFile && !message.codeChanges
        && (message.errorCode === 'model_no_response' || (!message.content?.trim() && !message.isError));
}

export function getUnansweredQuestionIndex(messages: Message[]): number {
    for (let index = messages.length - 1; index >= 0; index--) {
        const message = messages[index];
        if (message.role === 'user') return index;
        if (!isUnansweredResponse(message)) return -1;
    }
    return -1;
}

export function prepareRetryTurn(messages: Message[], userMessage: Message) {
    return {userMessage, history: removeRetryTurn(messages)};
}
