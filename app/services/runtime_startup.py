"""Startup coordination for optional native runtime updates."""

from services.shutdown_guard import protected
from services.omlx_policy import refresh_external_mtp_capabilities
import asyncio
from datetime import datetime, timezone

import httpx

from logger import get_logger
from routers.deps import load_config_async, load_ui_language_async, save_config_async
from services.model_runtime_profiles import (
    get_model_profile,
    normalize_model_profile,
    normalize_loaded_model_profile,
    recommended_model_profile,
    save_model_profile,
)
from services.runtime_settings import apply_runtime_settings
from services.model_profile_defaults import hardware_model_profile
from services.vyact_runtime import start_configured_runtime
from services.pinned_runtime import pinned_updates, install_pinned_components, migration_packages, runtime_components, reuse_pinned_components

logger = get_logger(__name__)

_startup_state: dict = {"status": "not_required", "packages": []}
_action_lock = asyncio.Lock()


def get_startup_runtime_state() -> dict:
    return dict(_startup_state)


def runtime_load_error_code(error: Exception) -> str:
    """Map a concrete runtime load failure to a stable user-facing code."""
    from services.llm.errors import http_error_response_body, is_insufficient_memory_message

    detail = http_error_response_body(error) if isinstance(error, httpx.HTTPStatusError) else str(error)
    return "model_insufficient_memory" if is_insufficient_memory_message(detail) else "model_warmup_failed"


def mark_runtime_load_failed(error: Exception, model_id: str) -> str:
    global _startup_state
    error_code = runtime_load_error_code(error)
    _startup_state = {
        **_startup_state, "status": "load_failed", "error_code": error_code, "model": model_id,
    }
    return error_code


async def warm_loaded_vyact_model(
        model_id: str, language: str | None = None, runtime: str | None = None,
) -> bool:
    """Load and warm the model through the production-shaped chat prefix request."""
    if not model_id:
        return False
    from prompts import FORMAT_INSTRUCTION
    from routers.chat_helpers import load_system_prompt
    from services.conv_summary import build_summary_instruction
    from services.llm.warmup import warm_vyact_chat_prefix

    if runtime is None:
        config = await load_config_async()
        runtime = config.get("vyact_config", {}).get("runtime", "gguf")

    _, _, selected_system_prompt = await load_system_prompt("")
    general_chat_system_prompt = (
        selected_system_prompt or FORMAT_INSTRUCTION
    ) + build_summary_instruction("", False, request_conversation_title=True)
    await warm_vyact_chat_prefix(
        model_id,
        language if language is not None else await load_ui_language_async() or "",
        general_chat_system_prompt,
        runtime=runtime,
        raise_on_error=True,
    )
    return True


async def detect_native_runtime_updates(config: dict) -> dict:
    """Offer initial managed migration before comparing release-pinned versions."""
    global _startup_state
    if config.get("type") == "vyact" and config.get("vyact_config", {}).get("model_path"):
        await reuse_pinned_components(runtime_components(config))
    packages = migration_packages(config)
    if packages:
        _startup_state = {"status": "migration_required", "operation": "migration", "packages": packages}
        return get_startup_runtime_state()
    if config.get("type") == "vyact" and config.get("vyact_config", {}).get("model_path"):
        components = runtime_components(config)
        packages = pinned_updates(components)
    _startup_state = {"status": "update_available" if packages else "not_required", "packages": packages}
    return get_startup_runtime_state()


async def persist_loaded_model_profile(profile: dict, vyact_config: dict, runtime_status: dict) -> dict:
    """Reconcile saved/query settings with the actual context and acceleration."""
    source = {
        "model_path": vyact_config.get("model_path"),
        "runtime": vyact_config.get("runtime", "gguf"),
        **profile,
    }
    effective = normalize_loaded_model_profile(
        source, int(vyact_config.get("context_size") or profile.get("context_size") or 32768),
    )
    if effective["context_size"] != profile.get("context_size"):
        logger.info("[runtime] fitted profile model=%s context=%s->%s output=%s history=%s",
                    effective.get("model_path"), profile.get("context_size"), effective["context_size"],
                    effective["max_output_tokens"], effective["history_token_budget"])
    if runtime_status.get("mtp_fallback"):
        logger.warning("[runtime] MTP fallback model=%s failure=%s",
                       effective.get("model_path"), runtime_status.get("mtp_failure_code"))
        effective.update({
            "mtp_enabled": False,
            "mtp_failure_code": runtime_status.get("mtp_failure_code", "load_failed"),
            "mtp_failure_message": runtime_status.get("mtp_failure_message"),
            "mtp_failed_at": datetime.now(timezone.utc).isoformat(),
        })
    if any(profile.get(key) != value for key, value in effective.items()):
        effective = await save_model_profile(effective)
    vyact_config.update({key: effective.get(key) for key in (
        "context_size", "max_output_tokens", "history_token_budget", "temperature", "top_k", "top_p",
        "cpu_threads", "seed", "kv_cache_precision", "cache_quantization", "mtp_enabled",
        "mtp_failure_code", "mtp_failure_message", "mtp_failed_at",
    )})
    return effective


async def load_configured_vyact_model(config: dict | None = None) -> tuple[str, str]:
    """Load the persisted Vyact model and reapply its saved runtime profile."""
    config = config or await load_config_async()
    vyact_config = config.get("vyact_config", {})
    if config.get("type") != "vyact" or not vyact_config.get("model_path"):
        return "", ""
    common_settings = config.get("runtime_settings", {})
    profile = await get_model_profile(vyact_config["model_path"])
    if profile is None:
        profile = await asyncio.to_thread(
            hardware_model_profile,
            vyact_config["model_path"], vyact_config.get("runtime", "gguf"),
            vyact_config.get("repository"), vyact_config.get("context_size", 32768),
        )
        profile = await save_model_profile(profile)
    else:
        migrated_profile = normalize_model_profile({
            **profile,
            "history_token_budget": profile.get(
                "history_token_budget", common_settings.get("history_token_budget", 16384),
            ),
        })
        if any(profile.get(key) != value for key, value in migrated_profile.items()):
            profile = await save_model_profile(migrated_profile)
    vyact_config.update({key: profile.get(key) for key in (
        "context_size", "limits", "max_output_tokens", "temperature", "top_k", "top_p", "cache_quantization",
        "mtp_enabled", "kv_cache_precision", "performance_mode", "cpu_threads", "seed", "history_token_budget",
        "gpu_split_percentages",
        "gpu_manual_split_enabled",
    )})
    runtime_status: dict = {}
    try:
        model_id = await asyncio.to_thread(
            start_configured_runtime, vyact_config, config.get("debug_logging", False), runtime_status,
        )
        profile = await persist_loaded_model_profile(profile, vyact_config, runtime_status)
    except Exception:
        logger.exception("[runtime] startup load failed model=%s runtime=%s context=%s status=%s",
                         vyact_config.get("model_path"), vyact_config.get("runtime"),
                         vyact_config.get("context_size"), runtime_status)
        raise
    config["model"] = model_id
    vyact_config["model"] = model_id
    apply_runtime_settings({
        **common_settings,
        "llm_num_ctx": profile["context_size"],
        "llm_num_predict": profile["max_output_tokens"],
        "llm_max_tokens": profile["max_output_tokens"],
        "llm_temperature": profile["temperature"],
        "top_k": profile.get("top_k"),
        "top_p": profile.get("top_p"),
        "seed": profile.get("seed"),
        "history_token_budget": profile.get("history_token_budget", common_settings.get("history_token_budget", 16384)),
    })
    await save_config_async(config)
    return model_id, await load_ui_language_async() or ""


@protected("installation")
async def apply_pinned_runtime_updates(config: dict) -> None:
    global _startup_state
    components = runtime_components(config)
    packages = pinned_updates(components)
    if not packages:
        raise RuntimeError("No pinned runtime update is available")
    try:
        await install_pinned_components([package["name"] for package in packages])
    except Exception:
        _startup_state = {**_startup_state, "status": "update_failed"}
        raise
    if "omlx" in components:
        await asyncio.to_thread(refresh_external_mtp_capabilities, True)


@protected("installation")
async def apply_runtime_migration(config: dict) -> None:
    global _startup_state
    # Re-evaluate the filesystem on every retry; never reinstall completed work.
    packages = migration_packages(config)
    if not packages:
        return
    try:
        await install_pinned_components([package["name"] for package in packages])
    except Exception:
        _startup_state = {**_startup_state, "status": "migration_failed", "operation": "migration"}
        raise
    if any(package["name"] == "omlx" for package in packages):
        await asyncio.to_thread(refresh_external_mtp_capabilities, True)


async def apply_startup_runtime_choice(update: bool) -> tuple[str, str]:
    global _startup_state
    async with _action_lock:
        if _startup_state.get("status") == "ready":
            return "", ""
        if update:
            migrating = _startup_state.get("operation") == "migration"
            _startup_state = {**_startup_state, "status": "migrating" if migrating else "updating"}
            config = await load_config_async()
            if migrating:
                await apply_runtime_migration(config)
            else:
                await apply_pinned_runtime_updates(config)
        _startup_state = {**_startup_state, "status": "loading_model"}
        result = await load_configured_vyact_model()
        try:
            await warm_loaded_vyact_model(*result)
        except Exception as error:
            error_code = mark_runtime_load_failed(error, result[0])
            raise RuntimeError(error_code) from error
        _startup_state = {"status": "ready", "packages": []}
        return result
