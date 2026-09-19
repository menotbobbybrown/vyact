"""Extract explicit web references from provider-independent MCP results."""
import json
import re
from typing import Any
from urllib.parse import urlsplit


_SOURCE_CONTAINERS = ("sources", "results", "references", "citations", "data")
_TITLE_URL_PAIR = re.compile(r"^Title:[ \t]*([^\r\n]+)\r?\nURL:[ \t]*(https?://[^\s]+)[ \t]*$", re.MULTILINE)
_MAX_SOURCES = 100


def extract_mcp_sources(result: Any) -> list[dict]:
    """Accept explicit title/url records, never arbitrary links in page content."""
    if getattr(result, "isError", False):
        return []
    sources: list[dict] = []
    seen: set[str] = set()

    def add(title: Any, url: Any) -> None:
        if not isinstance(title, str) or not isinstance(url, str):
            return
        title, url = title.strip(), url.strip()
        if not title or not url or len(sources) >= _MAX_SOURCES:
            return
        if any(char.isspace() or ord(char) < 32 for char in url):
            return
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                return
            parsed.port  # Reject malformed ports as well as malformed host literals.
        except ValueError:
            return
        if url in seen:
            return
        seen.add(url)
        sources.append({"title": title[:500], "url": url, "source": "web"})

    def visit(value: Any, depth: int = 0) -> None:
        if depth > 8 or len(sources) >= _MAX_SOURCES:
            return
        if isinstance(value, list):
            for item in value:
                visit(item, depth + 1)
        elif isinstance(value, dict):
            add(value.get("title"), value.get("url"))
            for key in _SOURCE_CONTAINERS:
                if key in value:
                    visit(value[key], depth + 1)

    visit(getattr(result, "structuredContent", None))
    for block in getattr(result, "content", []) or []:
        if getattr(block, "type", None) != "text":
            continue
        text = getattr(block, "text", "")
        if not isinstance(text, str):
            continue
        try:
            payload = json.loads(text)
        except (ValueError, RecursionError):
            for match in _TITLE_URL_PAIR.finditer(text):
                add(match.group(1), match.group(2))
        else:
            visit(payload)
    return sources
