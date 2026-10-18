"""Fixed-origin Vyvow API client. Credentials stay in the local backend."""
import calendar
from datetime import date, timedelta
from typing import Literal

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from logger import get_logger
from services.vyvow_credentials import read_token

logger = get_logger(__name__)

API_ROOT = "https://api.vyvow.com/api/member_place"
EXPENSE_CATEGORIES = (1, 2, 3, 12, 4, 5, 13, 6)
INCOME_CATEGORIES = (7, 8, 9, 10, 11)


class LedgerQuery(BaseModel):
    fromDate: date
    period: Literal["daily", "weekly", "monthly"] = "daily"
    tempTargetCurrency: str = Field(default="KRW", pattern=r"^[A-Z]{3}$")


class LedgerEntry(BaseModel):
    id: int = Field(default=0, ge=0)
    txType: Literal["INCOME", "EXPENSE"]
    houseLedgerOptionId: int
    memberBoardFileId: int = Field(default=0, ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    amount: float = Field(ge=0, le=100_000_000_000_000, allow_inf_nan=False)
    memo: str = Field(default="", max_length=120)
    tag: str = Field(default="", max_length=25)
    createdAt: date


async def request_api(method: str, endpoint: str, **kwargs) -> dict:
    token = await read_token()
    if not token:
        raise HTTPException(401, "vyvowLedger.tokenRequired")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            response = await client.request(method, f"{API_ROOT}/{endpoint}",
                                            headers={"X-Api-Key": token}, **kwargs)
        if response.status_code in (401, 403):
            raise HTTPException(401, "vyvowLedger.authFailed")
        response.raise_for_status()
        payload = response.json()
        code = payload.get("code", 200)
        if code in (401, 403):
            raise HTTPException(401, "vyvowLedger.authFailed")
        if code != 200:
            logger.warning("Vyvow API rejected %s: code=%s", endpoint, code)
            raise HTTPException(502, "vyvowLedger.requestFailed")
        return payload
    except (httpx.HTTPError, ValueError, AttributeError) as error:
        status = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
        logger.warning("Vyvow API failed %s: error=%s status=%s", endpoint, type(error).__name__, status)
        raise HTTPException(502, "vyvowLedger.requestFailed") from None


async def search_ledger(query: LedgerQuery) -> dict:
    params = {**query.model_dump(mode="json"), "init": True, "customPeriod": False}
    if query.period == "weekly":
        first = query.fromDate.replace(day=1)
        last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
        params.update(customPeriod=True,
                      fromDate=(first - timedelta(days=first.weekday())).isoformat(),
                      toDate=(last + timedelta(days=6 - last.weekday())).isoformat())
    payload = await request_api("POST", "searchHouseholdLedger", json=params)
    result = payload.get("result") or {}
    # Lombok serializes HLedger fields as hledgers/hledgerTags in production.
    return {"entries": result.get("hledgers", result.get("hLedgers", [])) or [],
            "currencies": result.get("exchangeRates") or [],
            "tags": result.get("hledgerTags", result.get("hLedgerTags", [])) or []}


async def save_entry(entry: LedgerEntry) -> dict:
    categories = INCOME_CATEGORIES if entry.txType == "INCOME" else EXPENSE_CATEGORIES
    if entry.houseLedgerOptionId not in categories:
        raise HTTPException(422, "vyvowLedger.invalidEntry")
    if entry.id:
        # The upstream update path fetches by ID; verify account ownership first.
        payload = await request_api("POST", "searchHouseholdLedger", json={
            "hLedgerId": entry.id, "fromDate": entry.createdAt.isoformat(), "period": "daily",
            "tempTargetCurrency": entry.currency, "init": False,
        })
        result = payload.get("result") or {}
        entries = result.get("hledgers", result.get("hLedgers", [])) or []
        if not any(item.get("id") == entry.id for item in entries):
            raise HTTPException(404, "vyvowLedger.entryUnavailable")
    await request_api("POST", "saveOrUpdateHLedger", json={
        "targetCurrency": entry.currency, "houseLedger": entry.model_dump(mode="json"),
    })
    return {"saved": True}
