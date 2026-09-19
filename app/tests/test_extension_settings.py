import pytest

from services.extension_settings import request_tool_settings, settings_events


@pytest.mark.asyncio
async def test_settings_events_deliver_target_and_clean_up():
    assert not request_tool_settings("web")
    events = settings_events()
    assert await anext(events) is None
    assert request_tool_settings("web")
    assert await anext(events) == {"tab": "api", "mcpServerId": "web"}
    await events.aclose()
    assert not request_tool_settings("web")


@pytest.mark.asyncio
async def test_settings_requests_keep_only_latest_target():
    events = settings_events()
    await anext(events)
    request_tool_settings("old")
    request_tool_settings("new")
    assert (await anext(events))["mcpServerId"] == "new"
    await events.aclose()
