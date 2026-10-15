"""Persisted prompt composition and request-local instruction fragments."""
import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
from copy import deepcopy
from functools import wraps
from inspect import isasyncgenfunction, signature

from elasticsearch import NotFoundError
from services.db import SETTINGS_INDEX, get_es

DOCUMENT_ID = "prompt_processing"
BUILTIN_IDS = ("base", "selectedPrompt", "project", "projectMemory", "personalMemory", "folders", "tone",
               "metadata", "external", "length", "reasoning", "date", "profile", "summary", "skills",
               "language", "tools", "toolContext", "mcp")
EDITABLE_IDS = {"base", "length", "reasoning", "tools"}
_settings_cache: tuple[dict, bool] | None = None
_settings_lock = asyncio.Lock()


def defaults(scope: str) -> list[dict]:
    excluded = {"project", "projectMemory"} if scope == "general" else {"personalMemory"}
    return [{"id": key, "enabled": True} for key in BUILTIN_IDS if key not in excluded]


def invalidate_settings_cache() -> None:
    global _settings_cache
    _settings_cache = None


async def load_settings(*, refresh: bool = False) -> tuple[dict, bool]:
    global _settings_cache
    if _settings_cache is not None and not refresh:
        return deepcopy(_settings_cache)
    async with _settings_lock:
        if _settings_cache is not None and not refresh:
            return deepcopy(_settings_cache)
        es = get_es()
        try:
            result = await es.get(index=SETTINGS_INDEX, id=DOCUMENT_ID)
            loaded = (result["_source"]["value"], True)
        except NotFoundError:
            loaded = ({scope: defaults(scope) for scope in ("general", "project")}, False)
        finally:
            await es.close()
        _settings_cache = deepcopy(loaded)
        return deepcopy(_settings_cache)


async def save_settings(settings: dict) -> None:
    global _settings_cache
    snapshot = deepcopy(settings)
    async with _settings_lock:
        es = get_es()
        try:
            await es.index(index=SETTINGS_INDEX, id=DOCUMENT_ID,
                           document={"key": DOCUMENT_ID, "value": snapshot}, refresh="wait_for")
        finally:
            await es.close()
        _settings_cache = (snapshot, True)


@dataclass
class PromptComposition:
    items: list[dict]
    parts: dict[str, str] = field(default_factory=dict)


current_composition: ContextVar[PromptComposition | None] = ContextVar("prompt_composition", default=None)


async def begin_composition(project_id: str = "", isolated: bool = False):
    if isolated:
        return current_composition.set(None)
    settings, _ = await load_settings()
    return current_composition.set(PromptComposition(deepcopy(settings["project" if project_id else "general"])))


def enabled(key: str) -> bool:
    composition = current_composition.get()
    return composition is None or any(item["id"] == key and item["enabled"] for item in composition.items)


def capture(key: str, text: str) -> str:
    """Return legacy text outside managed chats; collect named fragments inside them."""
    composition = current_composition.get()
    if composition is None:
        return text
    composition.parts[key] = text
    return ""


def append_part(current: str, key: str, text: str, *, extend: bool = False) -> str:
    composition = current_composition.get()
    if extend and composition is not None:
        text = "\n\n".join(filter(None, [composition.parts.get(key, ""), text]))
    fragment = capture(key, text)
    return f"{current}\n\n{fragment}" if current and fragment else current or fragment


def compose() -> str:
    composition = current_composition.get()
    if composition is None:
        return ""
    parts = []
    for item in composition.items:
        if not item["enabled"]:
            continue
        original = composition.parts.get(item["id"], "")
        # Conditional defaults (reasoning, tools, selected-prompt fallback) remain conditional.
        if item.get("source") != "user" and not original:
            continue
        text = (item.get("content", original) or "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def final_system_message(legacy: str) -> str:
    return compose() if current_composition.get() is not None else legacy


def chat_composition_only(function):
    """Keep indexing, decision, memory-analysis and other auxiliary LLM calls isolated."""
    parameters = signature(function)

    def token_for(args, kwargs):
        reason = parameters.bind_partial(*args, **kwargs).arguments.get("call_reason", "")
        return None if str(reason).startswith("chat:") else current_composition.set(None)

    if isasyncgenfunction(function):
        @wraps(function)
        async def stream(*args, **kwargs):
            token = token_for(args, kwargs)
            try:
                async for event in function(*args, **kwargs):
                    yield event
            finally:
                if token is not None:
                    current_composition.reset(token)
        return stream

    @wraps(function)
    async def query(*args, **kwargs):
        token = token_for(args, kwargs)
        try:
            return await function(*args, **kwargs)
        finally:
            if token is not None:
                current_composition.reset(token)
    return query
