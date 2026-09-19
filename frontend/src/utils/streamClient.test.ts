import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {streamSSE} from './streamClient';

vi.mock('../i18n', () => ({default: {t: (key: string) => key}}));

const frame = (event: string, data: object) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;

function respond(chunks: string[], keepOpen = false) {
    const cancel = vi.fn();
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
        start(controller) {
            for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
            if (!keepOpen) controller.close();
        },
        cancel,
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body)));
    return {body, cancel};
}

beforeEach(() => {
    vi.useFakeTimers();
    // Simulate a window that does not produce animation frames.
    vi.stubGlobal('requestAnimationFrame', vi.fn(() => 1));
    vi.stubGlobal('cancelAnimationFrame', vi.fn());
});
afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
});

describe('chat stream completion and cancellation', () => {
    it('preserves event order and completes when painting is suspended', async () => {
        const events: string[] = [];
        const {body, cancel} = respond([
            frame('meta', {model: 'local'}) + frame('token', {text: 'first'})
            + frame('token', {text: ' second'}) + frame('done', {answer: 'first second'})
            + frame('token', {text: 'ignored'}),
        ], true);
        const request = streamSSE('/stream', {}, {
            onMeta: data => events.push(data.model!),
            onToken: text => events.push(text),
            onDone: data => events.push(data.answer!),
        });
        await vi.runAllTimersAsync();
        await request;
        expect(events).toEqual(['local', 'first', ' second', 'first second']);
        expect(cancel).toHaveBeenCalledOnce();
        expect(body.locked).toBe(false);
        expect(vi.getTimerCount()).toBe(0);
    });

    it('uses an available animation frame without waiting for the fallback', async () => {
        respond([frame('token', {text: 'one'}) + frame('done', {answer: 'one'})]);
        const onDone = vi.fn();
        const request = streamSSE('/stream', {}, {onDone});
        await vi.advanceTimersByTimeAsync(0);
        const callback = vi.mocked(requestAnimationFrame).mock.calls[0][0];
        callback(0);
        await request;
        expect(onDone).toHaveBeenCalledOnce();
        expect(vi.getTimerCount()).toBe(0);
    });

    it('aborts during a suspended paint without dispatching buffered completion', async () => {
        const {body, cancel} = respond([frame('token', {text: 'one'}) + frame('done', {answer: 'one'})], true);
        const controller = new AbortController();
        const removeListener = vi.spyOn(controller.signal, 'removeEventListener');
        const onDone = vi.fn();
        const request = streamSSE('/stream', {}, {onDone}, controller.signal);
        const rejected = expect(request).rejects.toMatchObject({name: 'AbortError'});
        await vi.advanceTimersByTimeAsync(0);
        expect(requestAnimationFrame).toHaveBeenCalledOnce();
        controller.abort();
        await rejected;
        expect(onDone).not.toHaveBeenCalled();
        expect(cancel).toHaveBeenCalledOnce();
        expect(body.locked).toBe(false);
        expect(removeListener).toHaveBeenCalledWith('abort', expect.any(Function));
        expect(vi.getTimerCount()).toBe(0);
    });

    it.each(['', frame('token', {text: 'partial'}), 'event: done\ndata: {'])('rejects an incomplete stream: %j', async content => {
        const {body} = respond([content]);
        const onDone = vi.fn();
        await expect(streamSSE('/stream', {}, {onDone})).rejects.toThrow('main:networkError.streamFailed');
        expect(onDone).not.toHaveBeenCalled();
        expect(body.locked).toBe(false);
    });

    it('preserves split frames and completion without a trailing blank line', async () => {
        respond(['event: tok', 'en\ndata: {"text":"안녕"}\n', '\nevent: done\ndata: {"answer":"안녕"}']);
        const onToken = vi.fn();
        const onDone = vi.fn();
        await streamSSE('/stream', {}, {onToken, onDone});
        expect(onToken).toHaveBeenCalledWith('안녕');
        expect(onDone).toHaveBeenCalledExactlyOnceWith({answer: '안녕'});
    });

    it.each([true, false])('keeps server error handling with trailing separator=%s', async trailing => {
        const content = frame('error', {message: 'server failure'});
        respond([trailing ? content : content.trimEnd()]);
        const onError = vi.fn();
        await streamSSE('/stream', {}, {onError});
        expect(onError).toHaveBeenCalledExactlyOnceWith({message: 'server failure', model: undefined});
    });

    it('preserves read failures even when cancellation also fails', async () => {
        const body = new ReadableStream({start: controller => controller.error(new Error('read failed'))});
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body)));
        await expect(streamSSE('/stream', {}, {})).rejects.toThrow('read failed');
        expect(body.locked).toBe(false);
    });
});

it('reports cross-client queue state before streaming the response', async () => {
    respond([
        frame('queue', {waiting: true}) + frame('queue', {waiting: false})
        + frame('token', {text: 'Answer'}) + frame('done', {}),
    ]);
    const onQueue = vi.fn();
    const onToken = vi.fn();
    const work = streamSSE('/api/query/stream', {}, {onQueue, onToken});
    await vi.runAllTimersAsync();
    await work;
    expect(onQueue.mock.calls).toEqual([[{waiting: true}], [{waiting: false}]]);
    expect(onToken).toHaveBeenCalledWith('Answer');
});
