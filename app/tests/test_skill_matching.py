"""Selection boundaries and bootstrap wiring for prompt skills."""
import unittest
from unittest.mock import AsyncMock, patch

from routers import skills


class SkillMatchingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        routing = patch.object(skills, "route_local_skills", AsyncMock(return_value=None))
        routing.start()
        self.addCleanup(routing.stop)

    async def test_matching_score_boundaries(self):
        for scores, expected in [
            ([0.849, 0.84], []),
            ([0.85, 0.84], ["first"]),
            ([0.86, 0.85], ["first", "second"]),
            ([0.90, 0.85], ["first"]),
            ([0.85], ["first"]),
            ([], []),
        ]:
            with self.subTest(scores=scores):
                es = AsyncMock()
                es.search.side_effect = [{"hits": {"hits": []}}, {"hits": {"hits": [
                    {"_score": score, "_source": {"name": name, "instructions": name + " rules"}}
                    for name, score in zip(["first", "second"], scores)
                ]}}]
                with patch.object(skills, "get_es", return_value=es), patch.object(
                    skills, "get_embedding", AsyncMock(return_value=[0.1]),
                ):
                    result = await skills.match_skills("Check this analysis")
                self.assertEqual([item["name"] for item in result], expected)
                self.assertEqual(es.search.call_args.kwargs["knn"]["filter"], {"term": {"enabled": True}})
                es.close.assert_awaited_once()

    async def test_embedding_unavailable_skips_matching(self):
        es = AsyncMock()
        es.search.return_value = {"hits": {"hits": []}}
        with patch.object(skills, "get_es", return_value=es) as get_es, patch.object(
            skills, "get_embedding", AsyncMock(return_value=None),
        ):
            self.assertEqual(await skills.match_skills("Check this analysis"), [])
        es.close.assert_awaited_once()

    async def test_bootstrap_syncs_defaults_on_new_and_existing_installations(self):
        for exists in [True, False]:
            with self.subTest(index_exists=exists):
                es = AsyncMock()
                es.indices.exists.return_value = exists
                with patch.object(skills, "get_es", return_value=es), patch.object(
                    skills, "sync_default_skills", AsyncMock(),
                ) as sync:
                    await skills.ensure_skills_index()
                sync.assert_awaited_once_with(es, skills.get_embedding, initial_install=not exists)
                self.assertEqual(es.indices.create.await_count, int(not exists))
                es.close.assert_awaited_once()

    async def test_vector_fallback_does_not_inject_identical_content_twice(self):
        es = AsyncMock()
        hit = {"_score": 0.9, "_source": {"name": "review", "instructions": "Review"}}
        es.search.side_effect = [{"hits": {"hits": []}}, {"hits": {"hits": [hit, hit]}}]
        with patch.object(skills, "get_es", return_value=es), patch.object(
            skills, "get_embedding", AsyncMock(return_value=[0.1]),
        ):
            result = await skills.match_skills("Review code")
        self.assertEqual(len(result), 1)
