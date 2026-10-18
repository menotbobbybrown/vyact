"""Vyvow's user-managed API token, included in integration settings backups."""
from elasticsearch import NotFoundError

from services.db import INTEGRATION_SETTINGS_INDEX, get_es

TOKEN_DOCUMENT_ID = "vyvow_token"


async def read_token() -> str:
    es = get_es()
    try:
        document = await es.get(index=INTEGRATION_SETTINGS_INDEX, id=TOKEN_DOCUMENT_ID)
        return document.get("_source", {}).get("value", {}).get("token", "")
    except NotFoundError:
        return ""
    finally:
        await es.close()


async def save_token(token: str) -> None:
    es = get_es()
    try:
        await es.index(
            index=INTEGRATION_SETTINGS_INDEX,
            id=TOKEN_DOCUMENT_ID,
            document={"key": TOKEN_DOCUMENT_ID, "value": {"token": token.strip()}},
            refresh="wait_for",
        )
    finally:
        await es.close()
