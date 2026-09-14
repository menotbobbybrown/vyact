"""Loopback ports used only by Vyact-managed model processes."""
import functools
import logging
import socket
import threading

DEFAULT_RUNTIME_PORT = 19435
DEFAULT_MODEL_PORT = 19437
MAX_PORT_ATTEMPTS = 3
_runtime_port = DEFAULT_RUNTIME_PORT
_model_port = DEFAULT_MODEL_PORT
_launch_lock = threading.RLock()
logger = logging.getLogger(__name__)


def get_runtime_port() -> int:
    return _runtime_port


def get_model_port() -> int:
    return _model_port


def get_runtime_url() -> str:
    return f"http://127.0.0.1:{get_runtime_port()}/v1"


def _free_port(preferred: int, excluded: set[int]) -> int:
    for candidate in (preferred, *([0] * 20)):
        if candidate in excluded:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                listener.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            selected = listener.getsockname()[1]
            if selected not in excluded:
                return selected
    raise RuntimeError("No free loopback port for the Vyact runtime")


def is_port_conflict(error: Exception) -> bool:
    detail = f"{error}\n{getattr(error, 'diagnostic', '')}".lower()
    return any(marker in detail for marker in (
        "address already in use", "eaddrinuse", "10048", "only one usage of each socket address",
    ))


def with_runtime_ports(function):
    """Serialize launches and retry only bind conflicts, including selection races."""
    @functools.wraps(function)
    def launch(*args, **kwargs):
        global _runtime_port, _model_port
        with _launch_lock:
            previous_ports = (_runtime_port, _model_port)
            excluded = set()
            for attempt in range(MAX_PORT_ATTEMPTS):
                try:
                    _runtime_port = _free_port(DEFAULT_RUNTIME_PORT, excluded)
                    _model_port = _free_port(DEFAULT_MODEL_PORT, excluded | {_runtime_port})
                    logger.info("[runtime] Vyact loopback ports: API=%s, model=%s", _runtime_port, _model_port)
                    return function(*args, **kwargs)
                except BaseException as error:
                    if not isinstance(error, RuntimeError) or not is_port_conflict(error) or attempt == MAX_PORT_ATTEMPTS - 1:
                        _runtime_port, _model_port = previous_ports
                        raise
                    excluded.update((_runtime_port, _model_port))
    return launch
