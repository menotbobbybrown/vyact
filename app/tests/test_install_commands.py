import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from services.install_commands import run_install_command
from services.vyact_runtime import install_missing_runtime


class InstallCommandTests(unittest.TestCase):
    def test_failed_process_retains_stdout_stderr_command_and_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            log_file = Path(directory) / "event.log"
            command = [sys.executable, "-c", "import sys; print('progress'); print('untrusted tap', file=sys.stderr); sys.exit(1)"]
            with self.assertLogs("services.install_commands", level="INFO") as logs:
                code = asyncio.run(run_install_command(command, log_file))
            self.assertEqual(code, 1)
            for output in (log_file.read_text(), "\n".join(logs.output)):
                self.assertIn("progress", output)
                self.assertIn("untrusted tap", output)
                self.assertIn("Exit code: 1", output)
                self.assertIn(sys.executable, output)

    def test_spawn_error_is_logged(self):
        with tempfile.TemporaryDirectory() as directory:
            log_file = Path(directory) / "event.log"
            with self.assertRaises(FileNotFoundError):
                asyncio.run(run_install_command([str(Path(directory) / "missing")], log_file))
            self.assertIn("FileNotFoundError", log_file.read_text())

    def test_failed_pinned_install_is_not_hidden_by_existing_component(self):
        async def install():
            return [message async for message in install_missing_runtime()]
        with patch("services.vyact_runtime.managed_executable", return_value=None), \
             patch("services.vyact_runtime.install_pinned_components", new=AsyncMock(side_effect=RuntimeError("checksum mismatch"))):
            with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                asyncio.run(install())
