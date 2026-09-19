"""Optional execution hooks shared by internal tools and MCP calls."""
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class ToolExecution:
    name: str
    arguments: dict
    state: dict[str, Any] = field(default_factory=dict, repr=False)
    result: Any = None
    error: BaseException | None = None


ToolHook = Callable[[ToolExecution], Awaitable[None]]
ToolOperation = Callable[[ToolExecution], Awaitable[Any]]


@dataclass(frozen=True)
class ToolLifecycle:
    before: ToolHook | None = None
    after: ToolHook | None = None


async def run_tool_execution(execution: ToolExecution, operation: ToolOperation,
                             lifecycle: ToolLifecycle | None = None) -> Any:
    """Run after exactly once, including rejection, exception and cancellation.

    Hooks share request-local state, never global mutable execution state. After
    must tolerate an incomplete before hook. It can inspect the raw result or
    error; a returned tool-error payload remains a result, not an exception.
    A failed after hook propagates on success, but never masks an existing error.
    """
    try:
        if lifecycle and lifecycle.before:
            await lifecycle.before(execution)
        execution.result = await operation(execution)
        return execution.result
    except BaseException as error:
        execution.error = error
        raise
    finally:
        if lifecycle and lifecycle.after:
            try:
                await lifecycle.after(execution)
            except BaseException as error:
                if execution.error is None:
                    raise
                # Do not log hook arguments, state or exception text (credentials).
                logger.warning("[tools] cleanup failed for %s (%s)", execution.name, type(error).__name__)
