import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import CallToolResult, TextContent

from services.mcp_client import MCPManager, _Server
from services.mcp_sources import extract_mcp_sources


def result(text="", structured=None, error=False):
    return CallToolResult(content=[TextContent(type="text", text=text)],
                          structuredContent=structured, isError=error)


@pytest.mark.parametrize("container", ["sources", "results", "references", "citations"])
def test_structured_and_json_sources(container):
    record = {"title": "Example", "url": "https://example.com/article"}
    payload = {"data": {container: [record]}}
    expected = [{**record, "source": "web"}]
    assert extract_mcp_sources(result(structured=payload)) == expected
    assert extract_mcp_sources(result(json.dumps(payload))) == expected


def test_exa_text_and_duplicate_structured_results():
    text = "Title: First\nURL: https://example.com/1\nPublished: today\nHighlights: content\n\n---\n\nTitle: Second\nURL: https://example.com/2\nAuthor: Writer"
    sources = extract_mcp_sources(result(text, {"results": [{"title": "First", "url": "https://example.com/1"}]}))
    assert [s["title"] for s in sources] == ["First", "Second"]
    assert [s["url"] for s in sources] == ["https://example.com/1", "https://example.com/2"]


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///tmp/a", "https://", "https://user:pass@example.com", "https://example.com/a b", "https://example.com:bad", "https://[broken"])
def test_unsafe_or_invalid_urls_are_ignored(url):
    assert extract_mcp_sources(result(structured={"results": [{"title": "Bad", "url": url}]})) == []


def test_no_inferred_sources_from_body_or_arguments():
    assert extract_mcp_sources(result("Read [this](https://example.com).")) == []
    assert extract_mcp_sources(result("Title: Article\nBody: a linked URL\nURL: https://example.com")) == []
    assert extract_mcp_sources(result(structured={"arguments": {"title": "Input", "url": "https://example.com"}})) == []
    assert extract_mcp_sources(result(structured={"results": [{"url": "https://example.com"}]})) == []


def test_errors_and_source_limit():
    text = "Title: Failure\nURL: https://example.com"
    assert extract_mcp_sources(result(text, error=True)) == []
    records = [{"title": str(i), "url": f"https://example.com/{i}"} for i in range(110)]
    assert len(extract_mcp_sources(result(structured={"results": records}))) == 100


@pytest.mark.asyncio
async def test_external_call_keeps_text_and_delivers_sources_to_existing_drain():
    manager = MCPManager()
    response = result("Title: Source\nURL: https://example.com")
    session = SimpleNamespace(call_tool=AsyncMock(return_value=response))
    manager._workers["AnyProvider"] = SimpleNamespace(server=_Server("AnyProvider", session, []))
    with patch("services.mcp_client.get_tool_language", AsyncMock(return_value="en")):
        text = await manager.call_tool("AnyProvider__lookup", {})
    assert text == response.content[0].text
    assert manager.drain_tool_sources() == [{"title": "Source", "url": "https://example.com", "source": "web"}]
    assert manager.drain_tool_sources() == []
