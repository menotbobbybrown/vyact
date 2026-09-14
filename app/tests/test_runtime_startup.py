import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from services import runtime_startup


class RuntimeStartupTests(unittest.TestCase):
    def test_matching_runtime_versions_do_not_offer_update(self):
        config = {"type": "vyact", "vyact_config": {"model_path": "model.gguf"}}
        with patch.object(runtime_startup, "migration_packages", return_value=[]), \
             patch.object(runtime_startup, "pinned_updates", return_value=[]):
            self.assertEqual(asyncio.run(runtime_startup.detect_native_runtime_updates(config))["status"], "not_required")

    def test_migration_is_offered_without_review_and_waits_for_consent(self):
        packages = [{"name": "llama.cpp", "installed": "", "available": "b10809"}]
        with patch.object(runtime_startup, "migration_packages", return_value=packages), \
             patch.object(runtime_startup, "pinned_updates") as review, \
             patch.object(runtime_startup, "install_pinned_components", new=AsyncMock()) as install:
            status = asyncio.run(runtime_startup.detect_native_runtime_updates({}))
        self.assertEqual(status["status"], "migration_required")
        self.assertEqual(status["operation"], "migration")
        review.assert_not_called()
        install.assert_not_awaited()

    def test_migration_acceptance_installs_then_loads_and_warms(self):
        events = []
        async def install(components): events.append(("install", components))
        async def load():
            events.append(("load", []))
            return "model", "ko"
        packages = [{"name": "llama.cpp", "installed": "", "available": "b10809"}]
        with patch.object(runtime_startup, "_startup_state", {"status": "migration_required", "operation": "migration"}), \
             patch.object(runtime_startup, "load_config_async", new=AsyncMock(return_value={})), \
             patch.object(runtime_startup, "migration_packages", return_value=packages), \
             patch.object(runtime_startup, "install_pinned_components", side_effect=install), \
             patch.object(runtime_startup, "apply_pinned_runtime_updates", new=AsyncMock()) as review, \
             patch.object(runtime_startup, "load_configured_vyact_model", side_effect=load), \
             patch.object(runtime_startup, "warm_loaded_vyact_model", new=AsyncMock()) as warm:
            asyncio.run(runtime_startup.apply_startup_runtime_choice(True))
            self.assertEqual(runtime_startup.get_startup_runtime_state()["status"], "ready")
        self.assertEqual(events, [("install", ["llama.cpp"]), ("load", [])])
        review.assert_not_awaited()
        warm.assert_awaited_once_with("model", "ko")

    def test_migration_failure_remains_retryable_without_loading_model(self):
        with patch.object(runtime_startup, "_startup_state", {"status": "migration_required", "operation": "migration"}), \
             patch.object(runtime_startup, "load_config_async", new=AsyncMock(return_value={})), \
             patch.object(runtime_startup, "migration_packages", return_value=[{"name": "llama.cpp"}]), \
             patch.object(runtime_startup, "install_pinned_components", new=AsyncMock(side_effect=RuntimeError("download failed"))), \
             patch.object(runtime_startup, "load_configured_vyact_model", new=AsyncMock()) as load:
            with self.assertRaisesRegex(RuntimeError, "download failed"):
                asyncio.run(runtime_startup.apply_startup_runtime_choice(True))
            self.assertEqual(runtime_startup.get_startup_runtime_state()["status"], "migration_failed")
            self.assertEqual(runtime_startup.get_startup_runtime_state()["operation"], "migration")
        load.assert_not_awaited()

    def test_declining_migration_uses_existing_runtime_without_download(self):
        with patch.object(runtime_startup, "_startup_state", {"status": "migration_required", "operation": "migration"}), \
             patch.object(runtime_startup, "install_pinned_components", new=AsyncMock()) as install, \
             patch.object(runtime_startup, "load_configured_vyact_model", new=AsyncMock(return_value=("model", "en"))), \
             patch.object(runtime_startup, "warm_loaded_vyact_model", new=AsyncMock()):
            asyncio.run(runtime_startup.apply_startup_runtime_choice(False))
        install.assert_not_awaited()

    def test_new_pin_prompts_and_installs_only_after_acceptance(self):
        packages = [{"name": "llama.cpp", "installed": "b1", "available": "b2"}]
        config = {"type": "vyact", "vyact_config": {"model_path": "model.gguf"}}
        with patch.object(runtime_startup, "migration_packages", return_value=[]), \
             patch.object(runtime_startup, "pinned_updates", return_value=packages), \
             patch.object(runtime_startup, "load_config_async", new=AsyncMock(return_value=config)), \
             patch.object(runtime_startup, "install_pinned_components", new=AsyncMock()) as install, \
             patch.object(runtime_startup, "load_configured_vyact_model", new=AsyncMock(return_value=("model", "en"))), \
             patch.object(runtime_startup, "warm_loaded_vyact_model", new=AsyncMock()):
            status = asyncio.run(runtime_startup.detect_native_runtime_updates(config))
            self.assertEqual(status["status"], "update_available")
            install.assert_not_awaited()
            asyncio.run(runtime_startup.apply_startup_runtime_choice(True))
        install.assert_awaited_once_with(["llama.cpp"])

    def test_direct_update_rechecks_target_before_installing(self):
        with patch.object(runtime_startup, "pinned_updates", return_value=[]), \
             patch.object(runtime_startup, "install_pinned_components", new=AsyncMock()) as install:
            with self.assertRaisesRegex(RuntimeError, "No pinned"):
                asyncio.run(runtime_startup.apply_pinned_runtime_updates({}))
        install.assert_not_awaited()

    def test_saved_seed_is_reapplied_when_local_model_is_restored(self):
        profile = runtime_startup.recommended_model_profile(
            "owner/model.gguf", "gguf", "owner/model", 32768,
        )
        profile.update({
            "seed": 42,
            "mtp_enabled": False,
            "kv_cache_precision": "none",
            "cache_quantization": False,
        })
        apply_settings = Mock()
        config = {
            "type": "vyact",
            "runtime_settings": {},
            "vyact_config": {"runtime": "gguf", "model_path": "owner/model.gguf"},
        }
        with patch.object(
            runtime_startup, "load_config_async", new=AsyncMock(return_value=config),
        ), patch.object(
            runtime_startup, "get_model_profile", new=AsyncMock(return_value=profile),
        ), patch.object(
            runtime_startup, "start_configured_runtime", return_value="model-id",
        ), patch.object(
            runtime_startup, "apply_runtime_settings", new=apply_settings,
        ), patch.object(
            runtime_startup, "save_config_async", new=AsyncMock(),
        ), patch.object(
            runtime_startup, "load_ui_language_async", new=AsyncMock(return_value="ko"),
        ):
            result = asyncio.run(runtime_startup.load_configured_vyact_model())

        self.assertEqual(result, ("model-id", "ko"))
        self.assertEqual(apply_settings.call_args.args[0]["seed"], 42)

    def test_warms_loaded_model_with_the_shared_chat_prefix(self):
        prefix_warmup = AsyncMock(return_value=True)
        with patch(
            "routers.chat_helpers.load_system_prompt",
            new=AsyncMock(return_value=("", "", "Custom system prompt")),
        ), patch(
            "services.conv_summary.build_summary_instruction", return_value=" summary",
        ) as summary_instruction, patch(
            "services.llm.warmup.warm_vyact_chat_prefix", new=prefix_warmup,
        ):
            result = asyncio.run(runtime_startup.warm_loaded_vyact_model("model-id", "ko", "gguf"))

        self.assertTrue(result)
        summary_instruction.assert_called_once_with("", False, request_conversation_title=True)
        prefix_warmup.assert_awaited_once_with(
            "model-id", "ko", "Custom system prompt summary", runtime="gguf", raise_on_error=True,
        )

    def test_chat_warmup_failure_fails_model_activation(self):
        prefix_warmup = AsyncMock(side_effect=RuntimeError("warmup failed"))
        with patch(
            "routers.chat_helpers.load_system_prompt",
            new=AsyncMock(return_value=("", "", "System prompt")),
        ), patch(
            "services.conv_summary.build_summary_instruction", return_value="",
        ), patch(
            "services.llm.warmup.warm_vyact_chat_prefix", new=prefix_warmup,
        ):
            with self.assertRaisesRegex(RuntimeError, "warmup failed"):
                asyncio.run(runtime_startup.warm_loaded_vyact_model("model-id", "ko", "gguf"))

        prefix_warmup.assert_awaited_once()

    def test_startup_update_choice_warms_after_model_load(self):
        load_model = AsyncMock(return_value=("model-id", "en"))
        warmup = AsyncMock(return_value=True)
        with patch.object(
            runtime_startup, "_startup_state", {"status": "update_available", "packages": []},
        ), patch.object(
            runtime_startup, "load_config_async", new=AsyncMock(return_value={
                "type": "vyact", "vyact_config": {"runtime": "mlx", "model_path": "mlx/model"},
            }),
        ), patch.object(
            runtime_startup, "pinned_updates", return_value=[],
        ), patch.object(
            runtime_startup, "load_configured_vyact_model", new=load_model,
        ), patch.object(
            runtime_startup, "warm_loaded_vyact_model", new=warmup,
        ):
            result = asyncio.run(runtime_startup.apply_startup_runtime_choice(False))

        self.assertEqual(result, ("model-id", "en"))
        warmup.assert_awaited_once_with("model-id", "en")

    def test_startup_update_choice_exposes_warmup_failure(self):
        load_model = AsyncMock(return_value=("model-id", "en"))
        warmup = AsyncMock(side_effect=RuntimeError(
            "does not fit under the dynamic memory ceiling",
        ))
        state = {"status": "update_available", "packages": []}
        with patch.object(runtime_startup, "_startup_state", state), patch.object(
            runtime_startup, "load_configured_vyact_model", new=load_model,
        ), patch.object(
            runtime_startup, "warm_loaded_vyact_model", new=warmup,
        ):
            with self.assertRaisesRegex(RuntimeError, "model_insufficient_memory"):
                asyncio.run(runtime_startup.apply_startup_runtime_choice(False))

            self.assertEqual(runtime_startup.get_startup_runtime_state(), {
                "status": "load_failed",
                "packages": [],
                "error_code": "model_insufficient_memory",
                "model": "model-id",
            })


if __name__ == "__main__":
    unittest.main()
