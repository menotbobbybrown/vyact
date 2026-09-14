import asyncio
import ast
import os
import secrets
import tempfile
from pathlib import Path
import threading
import unittest
from unittest.mock import AsyncMock, patch

from anyio import CancelScope
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from routers import backup
from services import model_storage
from services.model_benchmark import BenchmarkGuard
from services import shutdown_guard as shutdown


class ShutdownGuardTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.guard = shutdown.ShutdownGuard()
        self.patch = patch.object(shutdown, "guard", self.guard)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_blocked_attempt_does_not_seal_and_no_timeout_overrides_it(self):
        with self.guard.operation("restore"):
            for _ in range(100):
                self.assertEqual(self.guard.prepare("quit"), {"allowed": False, "reasons": ["restore"]})
            with self.guard.operation("saving"):
                self.assertEqual(self.guard.prepare("quit")["reasons"], ["restore", "saving"])
        self.assertTrue(self.guard.prepare("quit")["allowed"])
        with self.assertRaises(shutdown.ShutdownPending):
            with self.guard.operation("restore"):
                self.fail("Cannot start after admission is sealed")

    def test_cancel_reopens_admission_and_rejects_late_prepare(self):
        self.assertTrue(self.guard.prepare("first")["allowed"])
        self.guard.cancel("first")
        self.assertFalse(self.guard.prepare("first")["allowed"])
        with self.guard.operation("saving"):
            self.assertFalse(self.guard.pending)
        self.assertTrue(self.guard.prepare("second")["allowed"])
        self.guard.cancel("first")
        self.assertTrue(self.guard.pending)

    async def test_disconnect_keeps_worker_protected_until_actual_completion(self):
        entered = threading.Event()
        finish = threading.Event()
        @shutdown.protected("saving")
        def write():
            entered.set()
            finish.wait(5)
        task = asyncio.create_task(asyncio.to_thread(write))
        await asyncio.to_thread(entered.wait, 2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.guard.prepare("quit")["reasons"], ["saving"])
        finish.set()
        await asyncio.to_thread(lambda: None)
        for _ in range(100):
            if self.guard.prepare("quit")["allowed"]:
                break
            await asyncio.sleep(.001)
        self.assertTrue(self.guard.pending)

    async def test_cancelled_async_mutation_completes_before_release(self):
        entered = asyncio.Event()
        finish = asyncio.Event()
        completed = asyncio.Event()
        @shutdown.protected("restore")
        async def restore():
            entered.set()
            await finish.wait()
            completed.set()
        task = asyncio.create_task(restore())
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        self.assertFalse(self.guard.prepare("quit")["allowed"])
        finish.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await completed.wait()
        await asyncio.sleep(0)
        self.assertTrue(self.guard.prepare("quit")["allowed"])

    async def test_disconnected_install_stream_finishes_without_releasing_early(self):
        finish = asyncio.Event()
        completed = asyncio.Event()
        @shutdown.protected("installation")
        async def install():
            yield "installing"
            await finish.wait()
            completed.set()
            yield "done"
        stream = install()
        self.assertEqual(await anext(stream), "installing")
        await stream.aclose()
        self.assertFalse(self.guard.prepare("quit")["allowed"])
        finish.set()
        await completed.wait()
        await asyncio.sleep(0)
        self.assertTrue(self.guard.prepare("quit")["allowed"])

    async def test_exception_releases_admission(self):
        @shutdown.protected("restore")
        async def fail():
            raise ValueError("failed")
        with self.assertRaises(ValueError):
            await fail()
        self.assertTrue(self.guard.prepare("quit")["allowed"])

    def test_worker_admission_and_prepare_are_atomic(self):
        for _ in range(30):
            guard = shutdown.ShutdownGuard()
            start = threading.Barrier(2)
            finish = threading.Event()
            entered = threading.Event()
            def worker():
                start.wait()
                try:
                    with guard.operation("restore"):
                        entered.set()
                        finish.wait(2)
                except shutdown.ShutdownPending:
                    pass
            thread = threading.Thread(target=worker)
            thread.start()
            start.wait()
            result = guard.prepare("quit")
            if result["allowed"]:
                self.assertFalse(entered.is_set())
            else:
                self.assertEqual(result["reasons"], ["restore"])
            finish.set()
            thread.join()


class ShutdownIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_restore_registration_survives_request_cancellation(self):
        guard = shutdown.ShutdownGuard()
        started = asyncio.Event()
        finish = asyncio.Event()
        async def read_backup(_file):
            started.set()
            await finish.wait()
            raise ValueError("Synthetic invalid backup; never write real data")
        with patch.object(shutdown, "guard", guard), patch.object(backup, "_read_backup", read_backup):
            task = asyncio.create_task(backup.import_backup(file=None))
            await started.wait()
            self.assertEqual(guard.prepare("quit")["reasons"], ["restore"])
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.assertFalse(guard.prepare("quit")["allowed"])
            finish.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0)
            self.assertTrue(guard.prepare("quit")["allowed"])

    async def test_document_cancel_keeps_temp_file_until_indexing_finishes(self):
        guard = shutdown.ShutdownGuard()
        started, finish = asyncio.Event(), asyncio.Event()
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory) / "source.txt"
            temporary.write_text("test document")
            @shutdown.protected("saving")
            async def index(path, _filename):
                started.set()
                await finish.wait()
                self.assertEqual(path.read_text(), "test document")
                return {"ok": True}
            # Load the real request cleanup code without module-level mkdir
            # against the user's installation directory.
            tree = ast.parse((Path(__file__).parents[1] / "routers" / "document.py").read_text())
            route = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "index_document")
            route.decorator_list = []
            route.args.args[0].annotation = None
            route.args.defaults = []
            namespace = {"_validate": lambda _: None, "_save_temp": AsyncMock(return_value=temporary),
                         "_index_saved_document": index, "HTTPException": HTTPException}
            exec(compile(ast.Module(body=[route], type_ignores=[]), "document-index", "exec"), namespace)
            with patch.object(shutdown, "guard", guard):
                task = asyncio.create_task(namespace["index_document"](file=type("Upload", (), {"filename": "source.txt"})()))
                await started.wait()
                task.cancel()
                await asyncio.sleep(0)
                task.cancel()  # Repeated cancellation must not release resources.
                await asyncio.sleep(0)
                self.assertTrue(temporary.exists())
                self.assertFalse(task.done())
                self.assertFalse(guard.prepare("quit")["allowed"])
                finish.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertFalse(temporary.exists())
                self.assertTrue(guard.prepare("quit")["allowed"])

    async def test_anyio_request_cancellation_keeps_resources_alive(self):
        guard = shutdown.ShutdownGuard()
        started, finish = asyncio.Event(), asyncio.Event()
        scopes = []
        events = []
        @shutdown.protected("saving")
        async def save():
            started.set()
            await finish.wait()
            events.append("saved")
        async def request():
            with CancelScope() as scope:
                scopes.append(scope)
                try:
                    await save()
                finally:
                    events.append("cleanup")
        with patch.object(shutdown, "guard", guard):
            task = asyncio.create_task(request())
            await started.wait()
            scopes[0].cancel()
            await asyncio.sleep(0)
            self.assertEqual(events, [])
            self.assertFalse(guard.prepare("quit")["allowed"])
            finish.set()
            await task
            self.assertEqual(events, ["saved", "cleanup"])

    async def test_storage_busy_middleware_allows_shutdown_reason_check(self):
        app = FastAPI()
        @app.post("/api/shutdown/prepare")
        async def prepare():
            return {"allowed": False, "reasons": ["storage"]}
        app.add_middleware(BenchmarkGuard)
        with patch.object(model_storage, "active_move", True):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/shutdown/prepare")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reasons"], ["storage"])

    async def test_installer_lifetime_and_safe_download_are_distinct(self):
        guard = shutdown.ShutdownGuard()
        for launch, should_block in [(shutdown.create_install_process, True), (shutdown.create_download_process, False)]:
            finish = asyncio.Event()
            process = AsyncMock()
            process.pid = 876543
            process.returncode = None
            process.wait.side_effect = lambda: None
            async def wait():
                await finish.wait()
                process.returncode = 0
            process.wait.side_effect = wait
            with patch.object(shutdown, "guard", guard), patch.object(shutdown.asyncio, "create_subprocess_exec", return_value=process):
                await launch("fake-only")
                self.assertEqual(guard.prepare("quit")["allowed"], not should_block)
                if not should_block:
                    self.assertIn(process.pid, shutdown.interruptible_download_pids())
                finish.set()
                await asyncio.sleep(0)
                guard.cancel("quit")
                guard = shutdown.ShutdownGuard()


class ShutdownEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_prepare_seals_and_cancel_reopens_http_admission(self):
        # Execute the actual route/middleware definitions without importing model
        # runtimes or running the production lifespan against user data.
        app = FastAPI()
        guard = shutdown.ShutdownGuard()
        names = {"_authorize_shutdown", "prepare_shutdown", "cancel_shutdown", "shutdown_admission", "shutdown_pending_handler"}
        tree = ast.parse((Path(__file__).parents[1] / "main.py").read_text())
        nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
        namespace = dict(app=app, os=os, secrets=secrets, Request=Request, JSONResponse=JSONResponse,
                         HTTPException=HTTPException, ShutdownPending=shutdown.ShutdownPending,
                         shutdown_guard=guard, interruptible_download_pids=lambda: [])
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "shutdown-endpoints", "exec"), namespace)
        @app.get("/api/read")
        async def read():
            return {"ok": True}
        headers = {"x-vyact-shutdown-token": "test-secret", "x-vyact-shutdown-attempt": "one"}
        with patch.dict(os.environ, {"VYACT_SHUTDOWN_TOKEN": "test-secret"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                self.assertEqual((await client.post("/api/shutdown/prepare")).status_code, 403)
                with guard.operation("restore"):
                    response = await client.post("/api/shutdown/prepare", headers=headers)
                    self.assertEqual(response.json()["reasons"], ["restore"])
                    self.assertEqual((await client.get("/api/read")).status_code, 200)
                response = await client.post("/api/shutdown/prepare", headers=headers)
                self.assertTrue(response.json()["allowed"])
                self.assertEqual(response.json()["pid"], os.getpid())
                self.assertEqual((await client.get("/api/read")).status_code, 503)
                self.assertEqual((await client.delete("/api/shutdown/prepare", headers=headers)).status_code, 200)
                self.assertEqual((await client.get("/api/read")).status_code, 200)
                self.assertFalse((await client.post("/api/shutdown/prepare", headers=headers)).json()["allowed"])


if __name__ == "__main__":
    unittest.main()
