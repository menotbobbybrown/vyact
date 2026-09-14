import copy
import json
import unittest
from unittest.mock import AsyncMock, patch

from routers.project import delete_project_memory_item, update_project_memory_item
from services import db
from services.conv_summary import HiddenMetadataStreamFilter, build_summary_instruction
from services import project_memory as pm


class ProjectMemoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.memory = {
            **pm.empty_project_memory(),
            'decisions': [{'id': 'd1', 'text': 'Use SQLite', 'status': 'active'}],
            'action_items': [{'id': 'a1', 'text': 'Run migration', 'status': 'active'}],
        }
        self.change = {'type': 'decision', 'id': 'd1', 'previous_text': 'Use SQLite', 'replacement': 'Use PostgreSQL'}

    async def merge(self, payload):
        es = AsyncMock()
        es.get.return_value = {'_source': {'memory': self.memory}}
        with patch.object(pm, 'get_es', return_value=es):
            await pm.merge_project_memory('project', 'conversation', payload)
        es.close.assert_awaited_once()
        return es.update.call_args.kwargs['doc']['memory']

    async def test_replace_and_complete_preserve_history_and_prompt(self):
        result = await self.merge({'updates': [self.change, {
            'type': 'action_item', 'id': 'a1', 'previous_text': 'Run migration', 'status': 'completed',
        }]})
        old, new = result['decisions']
        self.assertEqual(old['status'], 'superseded')
        self.assertEqual(old['superseded_by'], new['id'])
        self.assertEqual(new['supersedes'], old['id'])
        self.assertEqual(new['source_conv_id'], 'conversation')
        self.assertEqual(result['action_items'][0]['status'], 'completed')
        visible = pm.project_memory_prompt_view(result)
        self.assertEqual([item['text'] for item in visible['decisions']], ['Use PostgreSQL'])
        self.assertEqual(visible['decisions'][0]['id'], new['id'])
        pm._apply_memory_updates(result, [self.change], 'conversation')
        self.assertEqual(len(result['decisions']), 2)

    async def test_legacy_output_still_adds_and_deduplicates(self):
        result = await self.merge({'summary': 'Progress', 'decisions': ['Use SQLite', 'Use Redis'], 'action_items': ['Deploy']})
        self.assertEqual(len(result['decisions']), 2)
        self.assertEqual(len(result['action_items']), 2)
        self.assertEqual(result['summary'], 'Progress')
        self.assertEqual(result['decisions'][0]['status'], 'active')

    def test_invalid_or_ambiguous_updates_leave_items_unchanged(self):
        variants = [None, {}, [None], [self.change, self.change]]
        for overrides in [ {'id': 'other-project'}, {'previous_text': 'stale text'},
                           {'replacement': ''}, {'replacement': {}}, {'replacement': 'Use SQLite'},
                           {'type': 'unknown'}, {'id': []} ]:
            variants.append([{**self.change, **overrides}])
        variants.append([{'type': 'action_item', 'id': 'd1', 'previous_text': 'Use SQLite', 'status': 'completed'}])
        for updates in variants:
            with self.subTest(updates=updates):
                memory = copy.deepcopy(self.memory)
                pm._apply_memory_updates(memory, updates, 'conversation')
                self.assertEqual(memory, self.memory)

    async def test_non_project_or_bad_payload_does_not_access_database(self):
        with patch.object(pm, 'get_es') as get_es:
            await pm.merge_project_memory('', 'conversation', {'updates': [self.change]})
            await pm.merge_project_memory('project', 'conversation', ['bad'])
        get_es.assert_not_called()

    async def test_malformed_new_fields_do_not_break_legacy_save(self):
        result = await self.merge({'updates': 'bad', 'decisions': [None, {}, 'Use Redis'], 'action_items': [None, 'Deploy']})
        self.assertEqual(result['decisions'][-1]['text'], 'Use Redis')
        self.assertEqual(result['action_items'][-1]['text'], 'Deploy')

    def test_completed_decision_is_not_replaced(self):
        self.memory['decisions'][0]['status'] = 'completed'
        before = copy.deepcopy(self.memory)
        pm._apply_memory_updates(self.memory, [self.change], 'conversation')
        self.assertEqual(before, self.memory)

    def test_hidden_json_roundtrip_and_missing_tag(self):
        answer, payload = pm.extract_project_memory_tag('Answer<project_memory>{"updates":[]}</project_memory>')
        self.assertEqual((answer, payload), ('Answer', {'updates': []}))
        self.assertEqual(pm.extract_project_memory_tag('Answer'), ('Answer', None))

    def test_default_chat_prompt_is_unchanged_by_project_updates(self):
        general = build_summary_instruction('previous summary', False)
        project = build_summary_instruction('previous summary', False, self.memory)
        self.assertNotIn('project_memory', general)
        self.assertNotIn('previous_text', general)
        self.assertIn('previous_text', project)

    def test_updates_survive_every_stream_split_without_metadata_leak(self):
        response = 'Visible answer\n<project_memory>' + json.dumps({'updates': [self.change]}) + '</project_memory>'
        for split in range(len(response) + 1):
            stream_filter = HiddenMetadataStreamFilter()
            visible = stream_filter.feed(response[:split]) + stream_filter.feed(response[split:]) + stream_filter.finish()
            self.assertEqual(visible, 'Visible answer\n')
        clean, payload = pm.extract_project_memory_tag(response)
        self.assertEqual(clean, 'Visible answer')
        self.assertEqual(payload['updates'], [self.change])

    def test_old_items_without_ids_remain_visible_but_cannot_be_updated(self):
        del self.memory['decisions'][0]['id']
        before = copy.deepcopy(self.memory)
        self.assertEqual(pm.project_memory_prompt_view(self.memory)['decisions'][0]['text'], 'Use SQLite')
        pm._apply_memory_updates(self.memory, [self.change], 'conversation')
        self.assertEqual(before, self.memory)

    def test_prompt_excluded_items_cannot_be_changed(self):
        self.memory['decisions'] += [
            {'id': f'd{i}', 'text': f'Decision {i}', 'status': 'active'} for i in range(2, 53)
        ]
        before = copy.deepcopy(self.memory)
        pm._apply_memory_updates(self.memory, [self.change], 'conversation')
        self.assertEqual(before, self.memory)

    async def test_completed_task_replay_does_not_create_duplicate_task(self):
        update = {'type': 'action_item', 'id': 'a1', 'previous_text': 'Run migration', 'status': 'completed'}
        await self.merge({'updates': [update]})
        result = await self.merge({'updates': [update], 'action_items': ['Run migration']})
        self.assertEqual(len(result['action_items']), 1)
        self.assertEqual(result['action_items'][0]['status'], 'completed')

    async def test_storage_failure_is_contained_and_connection_closed(self):
        es = AsyncMock()
        es.get.side_effect = RuntimeError('database unavailable')
        with patch.object(pm, 'get_es', return_value=es):
            await pm.merge_project_memory('project', 'conversation', {'updates': [self.change]})
        es.update.assert_not_awaited()
        es.close.assert_awaited_once()

    async def test_manual_completion_reactivation_and_delete_still_work(self):
        es = AsyncMock()
        es.get.return_value = {'_source': {'memory': self.memory}}
        with patch.object(db, 'get_es', return_value=es):
            completed = await update_project_memory_item('project', 'action_item', 'a1', {'status': 'completed'})
            self.assertEqual(completed['action_items'][0]['status'], 'completed')
            active = await update_project_memory_item('project', 'action_item', 'a1', {'status': 'active'})
            self.assertEqual(active['action_items'][0]['status'], 'active')
            pm._apply_memory_updates(self.memory, [self.change], 'conversation')
            result = await delete_project_memory_item('project', 'decision', 'd1')
            self.assertEqual(len(result['decisions']), 1)
            self.assertEqual(result['decisions'][0]['text'], 'Use PostgreSQL')
