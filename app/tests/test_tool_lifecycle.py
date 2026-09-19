import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services.mcp_client import MCPManager
from services.tool_lifecycle import ToolExecution, ToolLifecycle, run_tool_execution


@pytest.mark.asyncio
async def test_hooks_receive_raw_result_and_shared_state():
    events = []

    async def before(execution):
        execution.state['reserved'] = 1
        events.append('before')

    async def operation(execution):
        events.append('call')
        return {'text': 'result', 'sources': []}

    async def after(execution):
        events.append('after')
        assert execution.state == {'reserved': 1}
        assert execution.result['text'] == 'result'
        assert execution.error is None

    result = await run_tool_execution(ToolExecution('test', {}), operation, ToolLifecycle(before, after))
    assert result['text'] == 'result'
    assert events == ['before', 'call', 'after']


@pytest.mark.asyncio
@pytest.mark.parametrize('before_failure', [False, True])
@pytest.mark.parametrize('error_type', [ValueError, asyncio.CancelledError])
async def test_after_runs_on_exception_rejection_and_cancellation(before_failure, error_type):
    error = error_type()
    before = AsyncMock(side_effect=error if before_failure else None)
    operation = AsyncMock(side_effect=None if before_failure else error)
    after = AsyncMock()
    execution = ToolExecution('test', {})
    with pytest.raises(error_type):
        await run_tool_execution(execution, operation, ToolLifecycle(before, after))
    assert execution.error is error
    after.assert_awaited_once_with(execution)
    if before_failure:
        operation.assert_not_awaited()


@pytest.mark.asyncio
async def test_after_failure_does_not_mask_original_error():
    original = ValueError('original')
    with pytest.raises(ValueError) as caught:
        await run_tool_execution(ToolExecution('test', {}), AsyncMock(side_effect=original),
                                 ToolLifecycle(after=AsyncMock(side_effect=RuntimeError('cleanup'))))
    assert caught.value is original
    with pytest.raises(RuntimeError):
        await run_tool_execution(ToolExecution('test', {}), AsyncMock(return_value='ok'),
                                 ToolLifecycle(after=AsyncMock(side_effect=RuntimeError('cleanup'))))


@pytest.mark.asyncio
@pytest.mark.parametrize('external', [False, True])
async def test_manager_runs_hooks_for_internal_and_external_calls(external):
    manager = MCPManager()
    before, after = AsyncMock(), AsyncMock()
    if external:
        name = 'server__tool'
        handler = AsyncMock(return_value=SimpleNamespace(content=[SimpleNamespace(type='text', text='ok')]))
        manager._workers['server'] = SimpleNamespace(server=SimpleNamespace(session=SimpleNamespace(call_tool=handler)))
    else:
        name = 'test'
        handler = AsyncMock(return_value={'text': 'ok', 'sources': [{'url': 'https://example.com'}]})
        manager.register_internal_tool(name, 'description', {}, handler)
    manager.set_tool_lifecycle(name, ToolLifecycle(before, after))
    assert await manager.call_tool(name, {'query': 'hello'}) == 'ok'
    before.assert_awaited_once()
    after.assert_awaited_once()
    assert before.call_args.args[0] is after.call_args.args[0]
    assert after.call_args.args[0].arguments == {'query': 'hello'}
    if not external:
        assert manager.drain_tool_sources() == [{'url': 'https://example.com'}]
    manager.set_tool_lifecycle(name, None)
    assert await manager.call_tool(name, {}) == 'ok'
    assert after.await_count == 1
