import asyncio
from threading import Event
from unittest.mock import Mock

import pytest

import reranker


@pytest.mark.asyncio
async def test_cancelled_inference_finishes_before_next_request(monkeypatch):
    first_started = Event()
    release_first = Event()
    second_started = Event()
    calls = []

    def rank(query, passages, **kwargs):
        calls.append(query)
        if query == 'first':
            first_started.set()
            assert release_first.wait(5)
        else:
            second_started.set()
        return [{'corpus_id': 0, 'score': 0.9}]

    monkeypatch.setattr(reranker, '_reranker', Mock(rank=rank))
    docs = [{'title': 'Document', 'content': 'Content'}]
    first = asyncio.create_task(reranker.rerank('first', docs))
    second = None
    try:
        assert await asyncio.to_thread(first_started.wait, 3)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        second = asyncio.create_task(reranker.rerank('second', docs))
        # The original GPU worker is still running after the HTTP waiter is cancelled.
        assert not await asyncio.to_thread(second_started.wait, 0.1)
        release_first.set()
        result = await asyncio.wait_for(second, 3)
        assert result[0]['rerank_score'] == 0.9
        assert calls == ['first', 'second']
        assert docs == [{'title': 'Document', 'content': 'Content'}]
    finally:
        release_first.set()
        if second is not None and not second.done():
            await asyncio.wait_for(second, 3)
