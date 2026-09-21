"""Managed defaults retain switches while user-owned content stays editable."""
import copy
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services import default_skills as migration
from services.llm.tools import build_tool_directive
from routers import skills as router
from fastapi import HTTPException
from elasticsearch import ConflictError

SKILL = {"name": "review", "description": "Review code", "instructions": "New rules", "version": 2}
OLD = {"name": "review", "description": "Review code", "instructions": "Old rules"}


class MemoryElasticsearch:
    def __init__(self, documents=None):
        self.documents = copy.deepcopy(documents or {})

    async def index(self, *, id, document, op_type=None, **kwargs):
        if op_type == 'create' and id in self.documents:
            raise RuntimeError('conflict')
        self.documents[id] = copy.deepcopy(document)

    async def update(self, *, id, doc, **kwargs):
        self.documents[id].update(doc)

    async def delete(self, *, id, **kwargs):
        del self.documents[id]


async def scan(es, **kwargs):
    for identifier, source in list(es.documents.items()):
        yield {'_id': identifier, '_source': copy.deepcopy(source), '_seq_no': 1, '_primary_term': 1}


class DefaultSkillsMigrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for replacement in [patch.object(migration, 'DEFAULT_SKILLS', [SKILL]),
                            patch.object(migration, 'LEGACY_FINGERPRINTS', {'review': migration.content_fingerprint(OLD)}),
                            patch.object(migration, 'async_scan', scan)]:
            replacement.start()
            self.addCleanup(replacement.stop)
        self.embed = AsyncMock(return_value=[0.1])

    async def test_new_install_and_repeat_are_idempotent(self):
        es = MemoryElasticsearch()
        await migration.sync_default_skills(es, self.embed)
        await migration.sync_default_skills(es, self.embed)
        self.assertEqual(list(es.documents), ['builtin:review'])
        self.assertEqual(es.documents['builtin:review']['version'], 2)
        self.embed.assert_awaited_once()

    async def test_version_upgrade_preserves_off_and_reuses_embedding(self):
        es = MemoryElasticsearch({'builtin:review': {**OLD, 'origin': 'builtin', 'version': 1,
                                                     'enabled': False, 'embedding': [0.4]}})
        await migration.sync_default_skills(es, self.embed)
        self.assertEqual(es.documents['builtin:review']['instructions'], 'New rules')
        self.assertFalse(es.documents['builtin:review']['enabled'])
        self.embed.assert_not_awaited()

    async def test_newer_saved_version_is_not_downgraded(self):
        source = {**SKILL, 'version': 3, 'origin': 'builtin', 'instructions': 'Future rules'}
        es = MemoryElasticsearch({'builtin:review': source})
        await migration.sync_default_skills(es, self.embed)
        self.assertEqual(es.documents['builtin:review'], source)
        self.embed.assert_not_awaited()

    async def test_legacy_duplicates_move_to_fixed_id(self):
        es = MemoryElasticsearch({'a': {**OLD, 'enabled': False}, 'b': {**OLD, 'enabled': False}})
        await migration.sync_default_skills(es, self.embed)
        self.assertEqual(list(es.documents), ['builtin:review'])
        self.assertFalse(es.documents['builtin:review']['enabled'])

    async def test_customized_legacy_is_preserved_as_user_skill(self):
        es = MemoryElasticsearch({'a': {**OLD, 'instructions': 'My custom rules', 'enabled': True}})
        await migration.sync_default_skills(es, self.embed)
        self.assertEqual(es.documents['a']['instructions'], 'My custom rules')
        self.assertEqual(es.documents['a']['origin'], 'user')
        self.assertFalse(es.documents['builtin:review']['enabled'])

    async def test_embedding_failure_retains_legacy_until_retry(self):
        es = MemoryElasticsearch({'a': OLD})
        self.embed.return_value = None
        await migration.sync_default_skills(es, self.embed)
        self.assertEqual(es.documents, {'a': OLD})
        self.embed.return_value = [0.1]
        await migration.sync_default_skills(es, self.embed)
        self.assertEqual(list(es.documents), ['builtin:review'])

    async def test_newer_duplicate_is_not_deleted_before_its_content_is_preserved(self):
        es = MemoryElasticsearch({
            'builtin:review': {**SKILL, 'origin': 'builtin', 'enabled': False},
            'duplicate': {**SKILL, 'origin': 'builtin', 'version': 3,
                          'instructions': 'Future rules', 'embedding': [0.1], 'enabled': True},
        })
        await migration.sync_default_skills(es, self.embed)
        self.assertEqual(list(es.documents), ['builtin:review'])
        self.assertEqual(es.documents['builtin:review']['version'], 3)
        self.assertEqual(es.documents['builtin:review']['instructions'], 'Future rules')
        self.assertFalse(es.documents['builtin:review']['enabled'])

    async def test_conflict_reloads_before_retry(self):
        es = MemoryElasticsearch()
        conflict = ConflictError('concurrent write', meta=MagicMock(status=409), body={})
        with patch.object(migration, '_sync_default_skills', AsyncMock(side_effect=[conflict, None])) as sync:
            await migration.sync_default_skills(es, self.embed)
        self.assertEqual(sync.await_count, 2)

    async def test_concurrent_retry_is_bounded(self):
        conflict = ConflictError('concurrent write', meta=MagicMock(status=409), body={})
        with patch.object(migration, '_sync_default_skills', AsyncMock(side_effect=conflict)) as sync:
            await migration.sync_default_skills(MemoryElasticsearch(), self.embed)
        self.assertEqual(sync.await_count, migration.SYNC_MAX_ATTEMPTS)


class BuiltinApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_edit_and_delete_rejected_but_toggle_allowed(self):
        es = AsyncMock()
        es.get.return_value = {'_source': {**SKILL, 'origin': 'builtin'}}
        with patch.object(router, 'get_es', return_value=es):
            for operation in [router.update_skill('builtin:review', router.SkillUpdate(instructions='overwrite')),
                              router.delete_skill('builtin:review')]:
                with self.assertRaises(HTTPException) as error:
                    await operation
                self.assertEqual(error.exception.status_code, 403)
            es.update.assert_not_awaited()
            es.delete.assert_not_awaited()
            await router.update_skill('builtin:review', router.SkillUpdate(enabled=False))
            self.assertFalse(es.update.call_args.kwargs['doc']['enabled'])


class RecipientDirectiveTests(unittest.IsolatedAsyncioTestCase):
    async def test_google_and_microsoft_writes_get_verification_without_skills(self):
        with patch("services.mcp_config.get_active_mcp_prompt", AsyncMock(return_value="CUSTOM PROMPT")):
            for tool in ["send_email", "create_email_draft", "reply_email", "create_calendar_event",
                         "update_calendar_event", "microsoft_send_email", "microsoft_create_calendar_event"]:
                with self.subTest(tool=tool):
                    directive = await build_tool_directive([tool])
                    self.assertIn("[Recipient verification", directive)
                    self.assertGreater(directive.index("[Recipient verification"), directive.index("CUSTOM PROMPT"))

    async def test_read_only_tools_do_not_receive_write_directive(self):
        with patch("services.mcp_config.get_active_mcp_prompt", AsyncMock(return_value="")):
            directive = await build_tool_directive(["search_emails"])
        self.assertNotIn("[Recipient verification", directive)
