"""Decision routing must never return invented free text or replace chat runtime."""
import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from services import decision_models as decision


@pytest.mark.parametrize('path', [
    'mlx/SirSahOl/Tev1-0.8B-experimental-chat-mlx-4bit',
    'ggml-org/Bespoke-Nimble-9B-v3-GGUF/model.gguf',
    'publisher/Tev1-4B-GGUF/q4.gguf',
])
def test_decision_families(path):
    assert decision.is_decision_model(path)


@pytest.mark.parametrize('path', ['publisher/my-nimble-chat', 'publisher/jev-model', 'bugrY/Qwen2.5-0.5B-Instruct-Gensyn-Swarm-nimble_pale_shrew'])
def test_family_boundary(path):
    # Family names are recognized; generic 'jev' names are not sufficient.
    assert not decision.is_decision_model(path)


def test_choices_are_explicit_unique_and_bounded():
    assert decision.explicit_choices('Choose\nA) yes\nB) no') == [('A', 'yes'), ('B', 'no')]
    assert decision.explicit_choices('A) yes\nA) no') == []
    assert decision.explicit_choices('A) yes') == []
    assert decision.explicit_choices('Write a summary') == []


@pytest.mark.asyncio
async def test_search_only_decision_families(monkeypatch):
    async def search(query, token):
        return [
            {'id': f'publisher/{query}-9B-GGUF', 'runtime': 'gguf', 'downloads': 2},
            {'id': 'publisher/qwen-chat', 'runtime': 'gguf', 'downloads': 100},
        ]
    monkeypatch.setattr(decision, 'search_gguf_models', search)
    monkeypatch.setattr(decision, 'is_apple_silicon', lambda: False)
    models = await decision.search_decision_models('tev1', False, None)
    assert [model['id'] for model in models] == ['publisher/Tev1-9B-GGUF']


@pytest.mark.asyncio
@pytest.mark.parametrize('result,expected', [('A', 'yes'), ('Z', None), ('A because it is correct', None), ('Q', None)])
async def test_only_exact_supplied_answer_is_returned(monkeypatch, result, expected):
    requests = []
    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200, json={'choices': [{'message': {'content': result}}]})
    client_type = httpx.AsyncClient
    monkeypatch.setattr(decision, '_runtime_lock', asyncio.Lock())
    monkeypatch.setattr(decision, '_start_decision_runtime', lambda settings: ('http://local/v1', 'decision'))
    monkeypatch.setattr(decision.httpx, 'AsyncClient', lambda **kwargs: client_type(transport=httpx.MockTransport(handle), **kwargs))
    answer = await decision.decide_chat('Choose\nA) yes\nB) no', {'model_path': 'publisher/Tev1-4B/q.gguf'})
    assert answer == expected
    assert requests[0]['temperature'] == 0
    assert requests[0]['max_tokens'] == decision.DECISION_MAX_TOKENS
    assert 'tools' not in requests[0]


@pytest.mark.asyncio
async def test_disabled_and_contextual_requests_do_not_return_direct_answer(monkeypatch):
    start = AsyncMock()
    monkeypatch.setattr(decision, '_start_decision_runtime', start)
    assert await decision.decide_chat('A) yes\nB) no', {}) is None
    start.assert_not_called()


@pytest.mark.asyncio
async def test_runtime_failure_falls_back(monkeypatch):
    monkeypatch.setattr(decision, '_runtime_lock', asyncio.Lock())
    def fail(settings):
        raise RuntimeError('out of memory')
    monkeypatch.setattr(decision, '_start_decision_runtime', fail)
    assert await decision.decide_chat('A) yes\nB) no', {'model_path': 'publisher/Tev1-4B/q.gguf'}) is None


@pytest.mark.asyncio
async def test_native_low_confidence_falls_back(monkeypatch):
    client_type = httpx.AsyncClient
    def handle(request):
        assert request.url.path == '/v1/systemone'
        payload = json.loads(request.content)
        assert payload['questions']['route']['type'] == 'choice'
        return httpx.Response(200, json={'answers': {'route': {'choice': 'A', 'confidence': 0.4}}})
    monkeypatch.setattr(decision, '_runtime_lock', asyncio.Lock())
    monkeypatch.setattr(decision, '_runtime_protocol', 'systemone')
    monkeypatch.setattr(decision, '_start_decision_runtime', lambda settings: ('http://local/v1', 'decision'))
    monkeypatch.setattr(decision.httpx, 'AsyncClient', lambda **kwargs: client_type(transport=httpx.MockTransport(handle), **kwargs))
    assert await decision.decide_chat('A) yes\nB) no', {'model_path': 'publisher/Nimble-9B/q.gguf'}) is None


@pytest.mark.asyncio
async def test_contextual_request_cannot_return_a_choice(monkeypatch):
    client_type = httpx.AsyncClient
    def handle(request):
        payload = json.loads(request.content)
        options = json.loads(payload['messages'][1]['content'])['options']
        assert all(option['label'] not in {'A', 'B'} for option in options)
        return httpx.Response(200, json={'choices': [{'message': {'content': 'A'}}]})
    monkeypatch.setattr(decision, '_runtime_lock', asyncio.Lock())
    monkeypatch.setattr(decision, '_runtime_protocol', 'chat')
    monkeypatch.setattr(decision, '_start_decision_runtime', lambda settings: ('http://local/v1', 'decision'))
    monkeypatch.setattr(decision.httpx, 'AsyncClient', lambda **kwargs: client_type(transport=httpx.MockTransport(handle), **kwargs))
    assert await decision.decide_chat('A) yes\nB) no', {'model_path': 'publisher/Tev1-4B/q.gguf'}, allow_direct=False) is None


@pytest.mark.asyncio
async def test_both_chat_entry_points_can_skip_llm(monkeypatch):
    from services.llm import core
    monkeypatch.setattr(core, 'load_config_async', AsyncMock(return_value={'decision_config': {'model_path': 'selected'}}))
    decide = AsyncMock(return_value='yes')
    provider = AsyncMock(side_effect=AssertionError('LLM should not be called'))
    monkeypatch.setattr(core, 'decide_chat', decide)
    monkeypatch.setattr(core, 'get_provider_config', provider)
    events = [event async for event in core.chat_stream_with_tools('A) yes\nB) no', [], call_reason='chat:general_stream')]
    assert events == [{'type': 'token', 'text': 'yes'}]
    assert await core.query_llm('A) yes\nB) no', [], call_reason='chat:general') == 'yes'
    provider.assert_not_called()


@pytest.mark.asyncio
async def test_selection_preserves_llm_and_concurrent_settings(monkeypatch):
    from routers import setup
    initial = {'type': 'vyact', 'vyact_config': {'model_path': 'chat-model'}, 'decision_config': {}}
    latest = {**initial, 'debug_logging': True}
    monkeypatch.setattr(setup, 'load_config_async', AsyncMock(side_effect=[initial, latest]))
    monkeypatch.setattr(setup, 'activate_decision_model', AsyncMock())
    save = AsyncMock()
    monkeypatch.setattr(setup, 'save_config_async', save)
    await setup.select_decision_model(setup.DecisionModelRequest(model_path='mlx/publisher/Tev1-0.8B-MLX'))
    saved = save.call_args.args[0]
    assert saved['vyact_config']['model_path'] == 'chat-model'
    assert saved['debug_logging'] is True
    assert saved['decision_config']['model_path'] == 'mlx/publisher/Tev1-0.8B-MLX'


@pytest.mark.asyncio
async def test_nimble_uses_specific_hub_search_name(monkeypatch):
    queries = []
    async def search(query, token):
        queries.append(query)
        return [{'id': 'ggml-org/Bespoke-Nimble-9B-v3-GGUF', 'runtime': 'gguf', 'downloads': 10}] if query == 'Bespoke-Nimble' else []
    monkeypatch.setattr(decision, 'search_gguf_models', search)
    monkeypatch.setattr(decision, 'is_apple_silicon', lambda: False)
    models = await decision.search_decision_models('Nimble', False, None)
    assert [model['id'] for model in models] == ['ggml-org/Bespoke-Nimble-9B-v3-GGUF']
    assert 'Bespoke-Nimble' in queries
