"""Persist subprocess diagnostics for setup and runtime installation."""
from services.shutdown_guard import create_install_process, create_download_process
import asyncio
import codecs
import json
import logging
from pathlib import Path

from logger import get_logger

logger = get_logger(__name__)


async def run_install_command(
    command: list[str], log_file: Path, *, cwd: str | None = None,
    env: dict[str, str] | None = None, interrupt_safe: bool = False,
) -> int:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    command_text = json.dumps(command, ensure_ascii=False)
    with log_file.open("a", encoding="utf-8") as output_log:
        def record(message: str, level: int = logging.INFO):
            logger.log(level, "[install] %s", message)
            output_log.write(message + "\n")
            output_log.flush()

        record(f"Command: {command_text}; cwd: {cwd or Path.cwd()}")
        process = None
        try:
            launch = create_download_process if interrupt_safe else create_install_process
            process = await launch(
                *command, stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                cwd=cwd, env=env,
            )
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            while chunk := await process.stdout.read(8192):
                decoded = decoder.decode(chunk)
                if decoded:
                    record(decoded.rstrip("\n"))
            remaining = decoder.decode(b"", final=True)
            if remaining:
                record(remaining)
            returncode = await process.wait()
            record(f"Exit code: {returncode}; command: {command_text}",
                   logging.ERROR if returncode else logging.INFO)
            return returncode
        except (Exception, asyncio.CancelledError) as error:
            record(f"Command failed: {command_text}; {type(error).__name__}: {error}", logging.ERROR)
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
            raise
