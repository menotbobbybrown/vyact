"""Atomic admission barrier for operations that cannot safely be interrupted.

A successful prepare seals admission until Electron kills the process or cancels
that attempt. No deadline can override active operations. Worker registrations
live in the worker itself, so disconnecting a client cannot release them early.
"""
import asyncio
import inspect
import threading
import os
import tempfile
from pathlib import Path
from collections import Counter
from contextlib import contextmanager
from functools import wraps

from anyio import CancelScope


class ShutdownPending(RuntimeError):
    pass


class ShutdownGuard:
    def __init__(self):
        self._lock = threading.Lock()
        self._active = Counter()
        self._attempt = None
        self._cancelled = set()

    @contextmanager
    def operation(self, reason):
        with self._lock:
            if self._attempt is not None:
                raise ShutdownPending("shutdown_pending")
            self._active[reason] += 1
        try:
            yield
        finally:
            with self._lock:
                self._active[reason] -= 1
                if not self._active[reason]:
                    del self._active[reason]

    def prepare(self, attempt):
        with self._lock:
            if attempt in self._cancelled:
                return {"allowed": False, "reasons": ["unavailable"]}
            if self._active:
                return {"allowed": False, "reasons": sorted(self._active)}
            if self._attempt not in (None, attempt):
                return {"allowed": False, "reasons": ["unavailable"]}
            self._attempt = attempt
            return {"allowed": True, "reasons": []}

    def cancel(self, attempt):
        with self._lock:
            self._cancelled.add(attempt)
            if self._attempt == attempt:
                self._attempt = None

    @property
    def pending(self):
        with self._lock:
            return self._attempt is not None


guard = ShutdownGuard()
_workers = set()


def protected(reason):
    """Keep async mutations alive on caller cancellation, including to_thread.

    Async generators retain admission across yields. Their installation child
    processes additionally retain their own registration until process exit.
    """
    def decorate(function):
        if inspect.isasyncgenfunction(function):
            @wraps(function)
            async def stream(*args, **kwargs):
                queue = asyncio.Queue()
                listening = True
                async def produce():
                    try:
                        with guard.operation(reason):
                            async for value in function(*args, **kwargs):
                                if listening:
                                    queue.put_nowait((value, None, False))
                    except Exception as error:
                        if listening:
                            queue.put_nowait((None, error, False))
                    finally:
                        queue.put_nowait((None, None, True))
                task = asyncio.create_task(produce())
                _workers.add(task)
                task.add_done_callback(_workers.discard)
                try:
                    while True:
                        value, error, done = await queue.get()
                        if done:
                            break
                        if error:
                            raise error
                        yield value
                finally:
                    listening = False
            return stream
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def asynchronous(*args, **kwargs):
                async def run():
                    with guard.operation(reason):
                        return await function(*args, **kwargs)
                task = asyncio.create_task(run())
                _workers.add(task)
                def finished(worker):
                    _workers.discard(worker)
                    if not worker.cancelled():
                        worker.exception()
                task.add_done_callback(finished)
                cancellation = None
                while True:
                    try:
                        # Keep the caller's UploadFile/temp files/locks alive
                        # until the worker has stopped using them. AnyIO request
                        # cancellation is level-triggered, so shield that scope
                        # as well as explicit asyncio Task.cancel() calls.
                        with CancelScope(shield=True):
                            result = await asyncio.shield(task)
                    except asyncio.CancelledError as error:
                        if task.cancelled():
                            raise
                        cancellation = error
                        continue
                    except Exception:
                        if cancellation is not None:
                            raise cancellation
                        raise
                    if cancellation is not None:
                        raise cancellation
                    return result
            return asynchronous
        @wraps(function)
        def synchronous(*args, **kwargs):
            with guard.operation(reason):
                return function(*args, **kwargs)
        return synchronous
    return decorate


@protected("installation")
async def create_install_process(*args, **kwargs):
    """A disconnected install stream must not make a live installer killable."""
    registration = guard.operation("installation")
    registration.__enter__()
    try:
        process = await asyncio.create_subprocess_exec(*args, **kwargs)
    except BaseException:
        registration.__exit__(None, None, None)
        raise

    async def watch():
        try:
            await process.wait()
        finally:
            registration.__exit__(None, None, None)
    task = asyncio.create_task(watch())
    _workers.add(task)
    task.add_done_callback(_workers.discard)
    return process


@protected("saving")
def atomic_write_bytes(path: Path, content: bytes):
    """Commit metadata/files without exposing a truncated previous version."""
    descriptor, temporary = tempfile.mkstemp(prefix=".vyact-write-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def atomic_write_text(path: Path, content: str, encoding="utf-8"):
    atomic_write_bytes(path, content.encode(encoding))


_download_processes = {}


@protected("runtime")
async def create_download_process(*args, **kwargs):
    """Cancellable cache download in an owned process group, not an installer."""
    if os.name != "nt":
        kwargs["start_new_session"] = True
    process = await asyncio.create_subprocess_exec(*args, **kwargs)
    _download_processes[process.pid] = process
    async def watch():
        try:
            await process.wait()
        finally:
            _download_processes.pop(process.pid, None)
    task = asyncio.create_task(watch())
    _workers.add(task)
    task.add_done_callback(_workers.discard)
    return process


def interruptible_download_pids():
    return [pid for pid, process in _download_processes.items() if process.returncode is None]
