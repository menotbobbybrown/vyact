"""Persist Tavily credit estimates separately from editable MCP configuration."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import math

import httpx

from services.db import INTEGRATION_SETTINGS_INDEX, get_es

USAGE_URL = "https://api.tavily.com/usage"
BASIC_SEARCH_CREDITS = 1
# The desktop backend has one process. Serialize refreshes and searches so a
# refresh cannot overwrite a debit and two searches cannot spend the last credit.
credit_lock = asyncio.Lock()


def _credit_summary(data: dict, usage_field: str, limit_field: str) -> dict:
    def number(field: str) -> int | float | None:
        value = data.get(field)
        return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None

    used, limit = number(usage_field), number(limit_field)
    return {"used": used, "limit": limit,
            "remaining": max(0, limit - used) if used is not None and limit is not None else None}


async def get_web_search_usage(api_key: str) -> dict:
    if not api_key.strip():
        return {"status": "missing_key"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(USAGE_URL, headers={"Authorization": f"Bearer {api_key.strip()}"})
        if response.status_code in (401, 403):
            return {"status": "invalid_key"}
        if response.status_code == 429:
            return {"status": "rate_limited"}
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("account"), dict):
            return {"status": "unavailable"}
        account = payload["account"]
        key = payload.get("key") if isinstance(payload.get("key"), dict) else {}
        return {
            "status": "ok",
            "plan": _credit_summary(account, "plan_usage", "plan_limit"),
            "paygo": _credit_summary(account, "paygo_usage", "paygo_limit"),
            "key": _credit_summary(key, "usage", "limit"),
        }
    except (httpx.HTTPError, ValueError, TypeError):
        return {"status": "unavailable"}


def _document_id(api_key: str) -> str:
    return "web_search_usage:" + sha256(api_key.strip().encode()).hexdigest()


async def load_usage(api_key: str) -> dict | None:
    es = get_es()
    try:
        result = await es.get(index=INTEGRATION_SETTINGS_INDEX, id=_document_id(api_key), ignore=[404])
        return result["_source"]["value"] if result.get("found") else None
    finally:
        await es.close()


async def save_usage(api_key: str, usage: dict) -> None:
    es = get_es()
    try:
        document_id = _document_id(api_key)
        await es.index(index=INTEGRATION_SETTINGS_INDEX, id=document_id,
                       document={"key": document_id, "value": usage}, refresh=True)
    finally:
        await es.close()


async def _refresh_usage(api_key: str) -> dict:
    latest = await get_web_search_usage(api_key)
    if latest["status"] == "ok":
        latest.update(checked_at=datetime.now(timezone.utc).isoformat(), estimated=False)
        await save_usage(api_key, latest)
    elif latest["status"] == "invalid_key" or await load_usage(api_key) is None:
        await save_usage(api_key, latest)
    # A temporary refresh failure must not erase a known exhausted balance.
    return latest


async def refresh_web_search_usage(api_key: str) -> dict:
    if not api_key.strip():
        return {"status": "missing_key"}
    try:
        async with credit_lock:
            usage = await _refresh_usage(api_key)
            return {**usage, "available": has_credits(usage)} if usage.get("status") == "ok" else usage
    except Exception:
        # Never expose DB request bodies or credentials in an error response.
        return {"status": "unavailable"}


async def get_stored_web_search_usage(api_key: str) -> dict:
    if not api_key.strip():
        return {"status": "missing_key"}
    try:
        async with credit_lock:
            usage = await ensure_usage(api_key)
            return {**usage, "available": has_credits(usage)} if usage.get("status") == "ok" else usage
    except Exception:
        return {"status": "unavailable"}


async def ensure_usage(api_key: str) -> dict:
    """Call under credit_lock. Existing keys get a baseline on first use."""
    return await load_usage(api_key) or await _refresh_usage(api_key)


def has_credits(usage: dict) -> bool:
    if usage.get("status") != "ok" or usage.get("blocked"):
        return False
    key = usage.get("key", {})
    if key.get("limit") is not None and (key.get("remaining") or 0) < BASIC_SEARCH_CREDITS:
        return False
    remaining = sum((usage.get(scope, {}).get("remaining") or 0) for scope in ("plan", "paygo"))
    return remaining >= BASIC_SEARCH_CREDITS


async def web_search_available(api_key: str) -> bool:
    if not api_key.strip():
        return False
    try:
        async with credit_lock:
            return has_credits(await ensure_usage(api_key))
    except Exception:
        return False


def debit_usage(usage: dict, credits: int | float = BASIC_SEARCH_CREDITS) -> dict:
    updated = deepcopy(usage)
    pending = credits
    for scope in ("plan", "paygo"):
        summary = updated[scope]
        debit = min(pending, summary.get("remaining") or 0) if scope == "plan" else pending
        if summary.get("used") is not None:
            summary["used"] += debit
        if summary.get("remaining") is not None:
            summary["remaining"] = max(0, summary["remaining"] - debit)
        pending -= debit
    key = updated["key"]
    if key.get("used") is not None:
        key["used"] += credits
    if key.get("remaining") is not None:
        key["remaining"] = max(0, key["remaining"] - credits)
    updated.update(estimated=True, updated_at=datetime.now(timezone.utc).isoformat())
    return updated
