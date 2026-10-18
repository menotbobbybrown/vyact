"""Local settings endpoints; saved tokens are never returned to the renderer."""
from fastapi import APIRouter, Path
from pydantic import BaseModel, SecretStr

from services.vyvow_credentials import read_token, save_token
from services.vyvow_ledger import LedgerEntry, LedgerQuery, request_api, save_entry, search_ledger

router = APIRouter(prefix="/vyvow")


class TokenRequest(BaseModel):
    token: SecretStr


@router.get("/token")
async def token_status():
    return {"has_token": bool(await read_token())}


@router.put("/token")
async def update_token(request: TokenRequest):
    token = request.token.get_secret_value().strip()
    await save_token(token)
    return {"has_token": bool(token)}


@router.post("/ledger/search")
async def search_household_ledger(query: LedgerQuery):
    return await search_ledger(query)


@router.put("/ledger")
async def save_household_entry(entry: LedgerEntry):
    return await save_entry(entry)


@router.delete("/ledger/{entry_id}")
async def delete_household_entry(entry_id: int = Path(gt=0)):
    await request_api("DELETE", "deleteHLedger", params={"hLedgerId": entry_id})
    return {"deleted": True}
