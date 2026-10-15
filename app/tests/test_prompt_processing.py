import unittest
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from routers.prompt_processing import router
from services.llm.providers import openai_stream, gemini_stream, claude_stream
from unittest.mock import AsyncMock, patch

from prompts import build_system_message
from services.prompt_processing import (
    PromptComposition, current_composition, defaults, capture, compose, enabled,
    load_settings, save_settings, chat_composition_only, invalidate_settings_cache, begin_composition, normalize_settings,
)
from services.llm.prepare import prepare_request
from services.llm.tools import build_tool_directive
from routers.prompt_processing import PromptSettings
from pydantic import ValidationError


class PromptCompositionTests(unittest.TestCase):
    def setUp(self):
        self.token = current_composition.set(PromptComposition(defaults("general")))

    def tearDown(self):
        current_composition.reset(self.token)

    def test_all_disabled_has_no_automatic_system_instructions(self):
        for item in current_composition.get().items:
            item["enabled"] = False
        capture("selectedPrompt", "SELECTED")
        capture("metadata", "HIDDEN")
        result = build_system_message("LEGACY FALLBACK", None, "PROFILE", "SKILL", "SUMMARY", "ko", reasoning=True)
        self.assertEqual(result, "SELECTED")

    def test_order_edits_and_custom_instructions_follow_stored_order(self):
        current_composition.get().items = [
            {"id": "custom:x", "enabled": True, "source": "user", "content": "CUSTOM"},
            {"id": "language", "enabled": True},
            {"id": "length", "enabled": True, "content": "EDITED LENGTH"},
        ]
        result = build_system_message("", None, user_language="ko")
        self.assertTrue(result.startswith("CUSTOM\n\n[Response language]"))
        self.assertTrue(result.endswith("EDITED LENGTH"))
        self.assertNotIn("Current date", result)

    def test_selected_prompt_keeps_included_format_rules(self):
        capture("selectedPrompt", "SELECTED")
        result = build_system_message("", None)
        self.assertIn("SELECTED", result)
        self.assertIn("[Default writing format]", result)
        self.assertIn("<vyproject", result)
        self.assertIn("<followups>", result)
        self.assertIn("take precedence", result)

    def test_split_format_rules_can_be_excluded_independently(self):
        capture("selectedPrompt", "SELECTED")
        for item in current_composition.get().items:
            if item["id"] in {"projectOutput", "followups"}:
                item["enabled"] = False
        result = build_system_message("", None)
        self.assertIn("SELECTED", result)
        self.assertIn("[Default writing format]", result)
        self.assertNotIn("<vyproject", result)
        self.assertNotIn("<followups>", result)
        next(item for item in current_composition.get().items if item["id"] == "base")["enabled"] = False
        next(item for item in current_composition.get().items if item["id"] == "followups")["enabled"] = True
        result = build_system_message("", None)
        self.assertNotIn("[Default writing format]", result)
        self.assertIn("<followups>", result)

    def test_legacy_settings_migrate_without_changing_edits_or_existing_order(self):
        for state in (True, False):
            items = [{"id": "selectedPrompt", "enabled": True},
                     {"id": "base", "enabled": state, "content": "CUSTOM FORMAT"},
                     {"id": "date", "enabled": False}]
            migrated = normalize_settings({"general": items})["general"]
            self.assertEqual([item["id"] for item in migrated],
                             ["selectedPrompt", "base", "projectOutput", "followups", "date"])
            self.assertEqual(migrated[1]["content"], "CUSTOM FORMAT")
            self.assertEqual([item["enabled"] for item in migrated[2:4]], [state, state])
            self.assertEqual(len(items), 3)

    def test_request_selected_fragments_survive_bulk_exclusion(self):
        for item in current_composition.get().items:
            item["enabled"] = False
        for key in ("selectedPrompt", "external", "toolContext", "mcp"):
            self.assertTrue(enabled(key))
            capture(key, key)
        capture("personalMemory", "EXCLUDED MEMORY")
        self.assertEqual(compose(), "selectedPrompt\n\nexternal\n\ntoolContext\n\nmcp")

    def test_reasoning_override_is_still_conditional(self):
        current_composition.get().items = [{"id": "reasoning", "enabled": True, "content": "THINK"}]
        self.assertEqual(build_system_message("", None, reasoning=False), "")
        self.assertEqual(build_system_message("", None, reasoning=True), "THINK")

    def test_scopes_and_validation(self):
        self.assertNotIn("personalMemory", [item["id"] for item in defaults("project")])
        self.assertNotIn("project", [item["id"] for item in defaults("general")])
        valid = {scope: defaults(scope) for scope in ("general", "project")}
        PromptSettings.model_validate(valid)
        next(item for item in valid["general"] if item["id"] == "selectedPrompt")["content"] = "ILLEGAL"
        with self.assertRaises(ValidationError):
            PromptSettings.model_validate(valid)


class PromptRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        invalidate_settings_cache()
        self.token = current_composition.set(PromptComposition([
            {"id": item["id"], "enabled": False} for item in defaults("general")
        ]))

    async def asyncTearDown(self):
        current_composition.reset(self.token)

    async def test_preparation_preserves_history_and_attachments_but_skips_lookups(self):
        history = [{"role": "user", "content": "PREVIOUS"}, {"role": "assistant", "content": "ANSWER"}]
        with patch("services.llm.config.get_provider_config", AsyncMock(return_value={"is_local": False})), \
             patch("routers.deps.load_ui_language_async", AsyncMock(return_value="ko")), \
             patch("services.user_profile.get_profile_text", AsyncMock()) as profile, \
             patch("routers.skills.match_skills", AsyncMock()) as skills:
            _, system, user, messages, _ = await prepare_request(
                "CURRENT", [{"source": "file", "title": "attachment", "content": "ATTACHMENT"}], "", [],
                history, None, True, "openai",
            )
        self.assertEqual(system, "")
        self.assertIn("CURRENT", user)
        self.assertIn("ATTACHMENT", user)
        self.assertEqual(messages, history)
        profile.assert_not_awaited()
        skills.assert_not_awaited()

    async def test_tool_directive_is_excluded_from_system(self):
        with patch("services.mcp_config.get_active_mcp_prompt", AsyncMock(return_value="")) as mcp:
            self.assertEqual(await build_tool_directive(["test_tool"]), "")
        self.assertEqual(compose(), "")
        mcp.assert_awaited_once()

    async def test_auxiliary_call_is_isolated_and_context_restored(self):
        original = current_composition.get()
        @chat_composition_only
        async def auxiliary(call_reason="analysis"):
            self.assertIsNone(current_composition.get())
            return "OK"
        self.assertEqual(await auxiliary(), "OK")
        self.assertIs(current_composition.get(), original)

    async def test_es_save_and_load_uses_separate_settings_document(self):
        settings = {scope: defaults(scope) for scope in ("general", "project")}
        es = AsyncMock()
        es.get.return_value = {"_source": {"value": settings}}
        with patch("services.prompt_processing.get_es", return_value=es):
            await save_settings(settings)
            loaded, exists = await load_settings()
        self.assertEqual(loaded, settings)
        self.assertTrue(exists)
        self.assertEqual(es.index.call_args.kwargs["index"], "system_settings")
        self.assertEqual(es.index.call_args.kwargs["id"], "prompt_processing")
        self.assertEqual(es.index.call_args.kwargs["document"]["value"], settings)


class ProviderPayloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_providers_send_only_enabled_instructions_and_preserve_context(self):

        class Captured(Exception):
            pass

        class Client:
            body = None

            @asynccontextmanager
            async def stream(self, method, url, **kwargs):
                self.body = kwargs["json"]
                raise Captured()
                yield  # pragma: no cover

            async def post(self, url, **kwargs):
                self.body = kwargs["json"]
                raise Captured()

        history = [{"role": "user", "content": "PREVIOUS"}, {"role": "assistant", "content": "ANSWER"}]
        tool = {"type": "function", "function": {"name": "test_tool", "description": "test", "parameters": {"type": "object", "properties": {}}}}
        for provider in (openai_stream, gemini_stream, claude_stream):
            with self.subTest(provider=provider.__name__):
                token = current_composition.set(PromptComposition([
                    *[{"id": item["id"], "enabled": False} for item in defaults("general")],
                    {"id": "custom:x", "source": "user", "enabled": True, "content": "ONLY CUSTOM"},
                ]))
                try:
                    client = Client()
                    with patch("services.llm.providers.get_provider_config", AsyncMock(return_value={"is_local": False, "selection_type": "custom:test"})), \
                         patch("services.llm.providers._get_unified_tools", AsyncMock(return_value=([tool], ["test_tool"]))):
                        with self.assertRaises(Captured):
                            async for _ in provider(client, "test-model", "test-key", compose(), "CURRENT ATTACHMENT", history, history, [], 10):
                                pass
                    body = client.body
                    system = (body["messages"][0]["content"] if provider is openai_stream else
                              body["systemInstruction"]["parts"][0]["text"] if provider is gemini_stream else body["system"])
                    self.assertEqual(system, "ONLY CUSTOM")
                    self.assertIn("PREVIOUS", str(body))
                    self.assertIn("CURRENT ATTACHMENT", str(body))
                    self.assertNotIn("Current date:", str(body))
                finally:
                    current_composition.reset(token)


class PromptApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        invalidate_settings_cache()

    async def test_api_roundtrip_and_invalid_readonly_content(self):
        app = FastAPI()
        app.include_router(router, prefix="/api")
        settings = {scope: defaults(scope) for scope in ("general", "project")}
        settings["general"][0]["enabled"] = False
        es = AsyncMock()
        es.get.return_value = {"_source": {"value": settings}}
        with patch("services.prompt_processing.get_es", return_value=es):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.put("/api/prompt-processing", json=settings)
                self.assertEqual(response.status_code, 200)
                loaded = await client.get("/api/prompt-processing")
                self.assertFalse(loaded.json()["settings"]["general"][0]["enabled"])
                next(item for item in settings["general"] if item["id"] == "selectedPrompt")["content"] = "ILLEGAL"
                self.assertEqual((await client.put("/api/prompt-processing", json=settings)).status_code, 422)
        self.assertEqual(es.index.await_count, 1)


class PromptCacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        invalidate_settings_cache()
        self.settings = {scope: defaults(scope) for scope in ("general", "project")}
        self.es = AsyncMock()
        self.es.get.return_value = {"_source": {"value": self.settings}}

    async def asyncTearDown(self):
        invalidate_settings_cache()

    async def test_repeated_queries_read_es_once_and_return_independent_snapshots(self):
        with patch("services.prompt_processing.get_es", return_value=self.es):
            first, _ = await load_settings()
            first["general"][0]["enabled"] = False
            second, _ = await load_settings()
            token = await begin_composition()
            current_composition.reset(token)
        self.es.get.assert_awaited_once()
        self.assertTrue(second["general"][0]["enabled"])

    async def test_save_refreshes_cache_without_another_read(self):
        with patch("services.prompt_processing.get_es", return_value=self.es):
            await load_settings()
            self.settings["general"][0]["enabled"] = False
            await save_settings(self.settings)
            self.settings["general"][0]["enabled"] = True
            loaded, _ = await load_settings()
        self.assertFalse(loaded["general"][0]["enabled"])
        self.es.get.assert_awaited_once()

    async def test_failed_save_keeps_last_successful_cache(self):
        with patch("services.prompt_processing.get_es", return_value=self.es):
            await load_settings()
            self.settings["general"][0]["enabled"] = False
            self.es.index.side_effect = RuntimeError("ES unavailable")
            with self.assertRaises(RuntimeError):
                await save_settings(self.settings)
            loaded, _ = await load_settings()
        self.assertTrue(loaded["general"][0]["enabled"])

    async def test_restore_refresh_reads_new_settings(self):
        with patch("services.prompt_processing.get_es", return_value=self.es):
            await load_settings()
            self.settings["general"][0]["enabled"] = False
            loaded, _ = await load_settings(refresh=True)
        self.assertFalse(loaded["general"][0]["enabled"])
        self.assertEqual(self.es.get.await_count, 2)
