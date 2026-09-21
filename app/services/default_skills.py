"""Versioned built-in skills and safe conversion of legacy prompt records."""
from datetime import datetime, timezone
import asyncio
import hashlib
import json

from config.default_skills import DEFAULT_SKILLS
from logger import get_logger
from elasticsearch.helpers import async_scan
from elasticsearch import ConflictError

logger = get_logger(__name__)
SKILLS_INDEX = "skills"
_sync_lock = asyncio.Lock()
SYNC_MAX_ATTEMPTS = 2
CONTENT_FIELDS = ("name", "description", "instructions")
# SHA-256 of the exact v1 content, excluding enabled/timestamps/embedding.
LEGACY_FINGERPRINTS = {
    "code-review": "05f2d4739b273a2d6329dbcfedf2641851f3a0b87a80e6c83a5cc42a6e5cb0ee",
    "code-refactor": "7cef5af7afd15cd986c910c8e031044fcb5fee81c606edea9c83813950aec3c6",
    "api-design": "6a2f5c059c9b5ab8f316e4cae4124083066b4517ff96d355f062de08761cc1e4",
    "commit-message": "71ebef99c4c87d56ef1faffcf5b864275b72f22c6d761183090fe1cf15d472f8",
    "bug-analysis": "e12f99898409c3a4d33b98bba8aad7a10088610857a014bba2157d26c274b14c",
    "document-summary": "4ec6fe7699fd31c75238239c894e5e4c46547ffbf718d559c4df0f239cacfbac",
    "translate-review": "f5835e32efb0cf9c121c0a5561258fbae55f15e585c6646853d1731c33c5ef64",
    "sql-query": "fa07aa54b0a81bc3366ac5b669079095050811dc34d6f452534807182e7e96e1"
}


def content_fingerprint(skill: dict) -> str:
    content = {key: skill.get(key, "") for key in CONTENT_FIELDS}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def is_builtin_skill(source: dict, identifier: str = "") -> bool:
    if source.get("origin") == "user":
        return False
    if source.get("origin") == "builtin" or identifier.startswith("builtin:"):
        return True
    name = source.get("name")
    known = next((skill for skill in DEFAULT_SKILLS if skill["name"] == name), None)
    return content_fingerprint(source) == LEGACY_FINGERPRINTS.get(name) or (
        known is not None and content_fingerprint(source) == content_fingerprint(known)
    )


async def sync_default_skills(es, get_embedding, *, initial_install: bool = False):
    async with _sync_lock:
        for attempt in range(SYNC_MAX_ATTEMPTS):
            try:
                await _sync_default_skills(es, get_embedding, initial_install=initial_install)
                return
            except ConflictError:
                # Re-read sequence numbers and switches before retrying a concurrent write.
                logger.warning("[skills] Concurrent modification during sync (attempt %s)", attempt + 1)
        logger.warning("[skills] Default skill sync deferred until next startup")


async def _sync_default_skills(es, get_embedding, *, initial_install: bool = False):
    """Refresh managed content by version, preserving switches and custom legacy entries."""
    del initial_install  # Managed defaults exist on every installation, including upgrades.
    hits = [hit async for hit in async_scan(es, index=SKILLS_INDEX,
            query={"query": {"match_all": {}}, "seq_no_primary_term": True})]
    for skill in DEFAULT_SKILLS:
        identifier = f"builtin:{skill['name']}"
        matching = [hit for hit in hits if hit["_source"].get("name") == skill["name"]]
        target = next((hit for hit in hits if hit["_id"] == identifier), None)
        legacy = [hit for hit in matching if hit["_id"] != identifier
                  and is_builtin_skill(hit["_source"], hit["_id"])]
        customized = [hit for hit in matching if not is_builtin_skill(hit["_source"], hit["_id"])]
        for hit in customized:
            if hit["_source"].get("origin") != "user":
                await es.update(index=SKILLS_INDEX, id=hit["_id"], doc={"origin": "user"},
                    if_seq_no=hit["_seq_no"], if_primary_term=hit["_primary_term"], refresh=True)
        managed = ([target] if target else []) + legacy
        previous = max(managed, key=lambda hit: (
            hit["_source"].get("version", 0), hit["_source"].get("updated_at", ""), hit["_id"]
        )) if managed else None
        source = previous["_source"] if previous else {}
        desired = skill if source.get("version", 0) <= skill["version"] else {
            key: source[key] for key in (*CONTENT_FIELDS, "version")
        }
        if not target or target["_source"].get("version", 0) < desired["version"]:
            embedding = source.get("embedding") if source.get("description") == desired["description"] else None
            if not embedding:
                embedding = await get_embedding(desired["description"])
            if not embedding:
                logger.warning("[skills] Default skill upgrade deferred: %s", skill["name"])
                continue
            now = datetime.now(timezone.utc).isoformat()
            content = {**desired, "origin": "builtin", "embedding": embedding, "updated_at": now,
                       "created_at": source.get("created_at", now),
                       "enabled": target["_source"].get("enabled", True) if target else source.get("enabled", not bool(customized))}
            if target:
                await es.index(index=SKILLS_INDEX, id=identifier, document=content,
                    if_seq_no=target["_seq_no"], if_primary_term=target["_primary_term"], refresh=True)
            else:
                await es.index(index=SKILLS_INDEX, id=identifier, op_type="create", document=content, refresh=True)
        # Remove only recognized defaults after the canonical entry is durable.
        for hit in legacy:
            await es.delete(index=SKILLS_INDEX, id=hit["_id"],
                if_seq_no=hit["_seq_no"], if_primary_term=hit["_primary_term"], refresh=True)
