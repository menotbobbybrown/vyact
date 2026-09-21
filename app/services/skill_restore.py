"""Only user-owned skills participate in backup and restore."""
from uuid import NAMESPACE_URL, uuid5

from elasticsearch.helpers import async_scan

from services.default_skills import SKILLS_INDEX, is_builtin_skill


def filter_skill_backup_documents(index: str, documents: list[dict]) -> list[dict]:
    if index != SKILLS_INDEX:
        return documents
    return [document for document in documents
            if not is_builtin_skill(document.get('_source') or {}, document.get('_id', ''))]


async def filter_restored_skills(es, documents: list[dict]) -> tuple[list[dict], int]:
    candidates = {}
    for document in filter_skill_backup_documents(SKILLS_INDEX, documents):
        source = document.get('_source') or {}
        name = source.get('name')
        if not document.get('_id') or not isinstance(name, str) or not name:
            continue
        previous = candidates.get(name)
        if previous is None or _revision_key(document) > _revision_key(previous):
            candidates[name] = document
    if not candidates:
        return [], len(documents)
    existing = {}
    occupied = {}
    managed_ids = set()
    async for hit in async_scan(es, index=SKILLS_INDEX, query={'query': {'match_all': {}}}):
        occupied[hit['_id']] = hit['_source'].get('name')
        if is_builtin_skill(hit['_source'], hit['_id']):
            managed_ids.add(hit['_id'])
        else:
            name = hit['_source'].get('name')
            if name not in existing or _revision_key(hit) > _revision_key(existing[name]):
                existing[name] = hit
    selected = []
    for name, document in candidates.items():
        source = {**document['_source'], 'origin': 'user'}
        source.pop('version', None)
        identifier = existing[name]['_id'] if name in existing else document['_id']
        # Reserve managed IDs even for malformed/older backups marking them as user-owned.
        # Also avoid overwriting renamed entries or another document in this same import.
        suffix = 0
        while identifier in managed_ids or identifier.startswith('builtin:') or (
            identifier in occupied and occupied[identifier] != name
        ):
            seed = f"{document['_id']}:{name}:{suffix}"
            identifier = 'user-restored:' + str(uuid5(NAMESPACE_URL, seed))
            suffix += 1
        occupied[identifier] = name
        selected.append({'_id': identifier, '_source': source})
    return selected, len(documents) - len(selected)


def _revision_key(document: dict) -> tuple[str, str]:
    source = document['_source']
    return (source.get('updated_at') or source.get('created_at') or '', document['_id'])
