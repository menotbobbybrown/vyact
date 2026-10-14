"""Stable email identity for account-specific mail preferences."""
import hashlib

from services.db import GOOGLE_WORKSPACE_SETTINGS_INDEX, get_es

SETTING_PREFIXES = {
    "signature": ("microsoft_mail_signature:", "microsoft_signature_"),
    "recipient_groups": ("microsoft_recipient_groups:", "microsoft_recipient_groups:"),
}


def document_id(kind: str, email: str) -> str:
    account_key = hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()
    return SETTING_PREFIXES[kind][0] + account_key


async def migrate_legacy_settings(account_id: str, email: str) -> None:
    """Only migrate while the slot's existing credentials identify its owner."""
    if not email.strip():
        return
    es = get_es()
    try:
        for kind, (_, legacy_prefix) in SETTING_PREFIXES.items():
            legacy_id = legacy_prefix + account_id
            if not await es.exists(index=GOOGLE_WORKSPACE_SETTINGS_INDEX, id=legacy_id):
                continue
            key = document_id(kind, email)
            if not await es.exists(index=GOOGLE_WORKSPACE_SETTINGS_INDEX, id=key):
                source = (await es.get(index=GOOGLE_WORKSPACE_SETTINGS_INDEX, id=legacy_id))["_source"]
                await es.index(index=GOOGLE_WORKSPACE_SETTINGS_INDEX, id=key,
                               document={**source, "key": key}, refresh=True)
            await es.delete(index=GOOGLE_WORKSPACE_SETTINGS_INDEX, id=legacy_id, refresh=True)
    finally:
        await es.close()
