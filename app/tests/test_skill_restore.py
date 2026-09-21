import unittest
from unittest.mock import patch

from config.default_skills import DEFAULT_SKILLS
from services import skill_restore
from services.default_skills import SKILLS_INDEX
from app.tests.test_default_skills import MemoryElasticsearch, scan


def document(identifier, name, updated='2026-01-01', **extra):
    return {'_id': identifier, '_source': {'name': name, 'updated_at': updated, 'instructions': 'custom', **extra}}


class SkillRestoreTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        replacement = patch.object(skill_restore, 'async_scan', scan)
        replacement.start()
        self.addCleanup(replacement.stop)

    async def test_backup_and_restore_exclude_builtin_but_keep_same_named_user(self):
        default = DEFAULT_SKILLS[0]
        docs = [{'_id': 'legacy', '_source': default},
                document('builtin:code-review', 'code-review', origin='builtin'),
                document('user', 'code-review', origin='user')]
        exported = skill_restore.filter_skill_backup_documents(SKILLS_INDEX, docs)
        self.assertEqual([doc['_id'] for doc in exported], ['user'])
        selected, skipped = await skill_restore.filter_restored_skills(MemoryElasticsearch(), docs)
        self.assertEqual([doc['_id'] for doc in selected], ['user'])
        self.assertEqual(skipped, 2)

    async def test_user_backup_overwrites_existing_user_by_name_and_preserves_off(self):
        es = MemoryElasticsearch({'local': {'name': 'custom', 'origin': 'user', 'instructions': 'local'}})
        docs = [document('other-install', 'custom', enabled=False)]
        selected, skipped = await skill_restore.filter_restored_skills(es, docs)
        self.assertEqual(selected[0]['_id'], 'local')
        self.assertFalse(selected[0]['_source']['enabled'])
        self.assertEqual(skipped, 0)
        await es.index(id=selected[0]['_id'], document=selected[0]['_source'])
        again, _ = await skill_restore.filter_restored_skills(es, docs)
        self.assertEqual(again, selected)

    async def test_same_name_builtin_is_never_overwritten(self):
        es = MemoryElasticsearch({'builtin:code-review': {'name': 'code-review', 'origin': 'builtin'}})
        selected, _ = await skill_restore.filter_restored_skills(es, [document('user-id', 'code-review')])
        self.assertEqual(selected[0]['_id'], 'user-id')

    async def test_duplicate_backup_uses_latest(self):
        docs = [document('old', 'custom'), document('new', 'custom', '2026-02-01')]
        selected, skipped = await skill_restore.filter_restored_skills(MemoryElasticsearch(), docs)
        self.assertEqual(selected[0]['_id'], 'new')
        self.assertEqual(skipped, 1)

    async def test_user_marked_backup_cannot_overwrite_managed_id(self):
        es = MemoryElasticsearch({'builtin:code-review': {'name': 'code-review', 'origin': 'builtin'}})
        selected, _ = await skill_restore.filter_restored_skills(es, [
            document('builtin:code-review', 'code-review', origin='user')])
        self.assertTrue(selected[0]['_id'].startswith('user-restored:'))
        await es.index(id=selected[0]['_id'], document=selected[0]['_source'])
        again, _ = await skill_restore.filter_restored_skills(es, [
            document('builtin:code-review', 'code-review', origin='user')])
        self.assertEqual(again, selected)
        self.assertEqual(es.documents['builtin:code-review']['origin'], 'builtin')

    async def test_conflicting_backup_ids_for_different_names_are_separated(self):
        selected, _ = await skill_restore.filter_restored_skills(MemoryElasticsearch(), [
            document('shared-id', 'first'), document('shared-id', 'second')])
        self.assertEqual(len({item['_id'] for item in selected}), 2)

    async def test_legacy_builtin_id_is_reserved_even_without_prefix(self):
        es = MemoryElasticsearch({'old-random-id': {'name': 'code-review', 'origin': 'builtin'}})
        selected, _ = await skill_restore.filter_restored_skills(es, [
            document('old-random-id', 'code-review', origin='user')])
        self.assertNotEqual(selected[0]['_id'], 'old-random-id')
