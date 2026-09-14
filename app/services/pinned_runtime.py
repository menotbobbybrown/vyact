"""Release-selected runtimes, isolated from the user's package managers."""
import asyncio
import hashlib
import io
import json
import os
import platform
import re
import shutil
import sys
import tarfile
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

import httpx

from logger import get_logger
from config import INSTALL_DIR, get_log_file
from services.install_commands import run_install_command
from services.shutdown_guard import protected

RUNTIME_ROOT = INSTALL_DIR / "runtime"
VERSION_MANIFEST = Path(__file__).with_name("runtime_versions.json")
BUNDLED_RUNTIME_DIR = Path(__file__).resolve().parents[2] / "linux-runtime"
_install_lock = asyncio.Lock()
logger = get_logger(__name__)


def runtime_manifest() -> dict:
    return json.loads(VERSION_MANIFEST.read_text(encoding="utf-8"))


def platform_key() -> str:
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    return f"{platform.system()}-{machine}"


def _read_records(path: Path) -> dict:
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
        return records if isinstance(records, dict) else {}
    except (OSError, ValueError):
        return {}


def _record_executable(record: dict) -> Path | None:
    relative = record.get("executable")
    if not relative:
        return None
    executable = (RUNTIME_ROOT / relative).resolve()
    if RUNTIME_ROOT.resolve() not in executable.parents:
        return None
    return executable if executable.is_file() else None


def installed_runtime() -> dict:
    records = _read_records(BUNDLED_RUNTIME_DIR / "runtime-versions.json") if platform.system() == "Linux" else {}
    for component, record in _read_records(RUNTIME_ROOT / "installed-versions.json").items():
        # Older manifests could contain copied bundle metadata. Do not let that
        # shadow the version in a newly shipped bundle.
        if isinstance(record, dict) and record.get("executable") and (
            _record_executable(record) or component not in records
        ):
            records[component] = record
    return records


def managed_executable(component: str) -> Path | None:
    return _record_executable(_read_records(RUNTIME_ROOT / "installed-versions.json").get(component, {}))


def omlx_executable() -> str | None:
    managed = managed_executable("omlx")
    return str(managed) if managed else shutil.which("omlx")


def runtime_components(config: dict) -> list[str]:
    components = ["llama.cpp", "llama-swap"]
    if platform_key() == "Darwin-arm64" and (
        config.get("vyact_config", {}).get("runtime") == "mlx" or omlx_executable()
    ):
        components.append("omlx")
    return components


def migration_packages(config: dict) -> list[dict]:
    """Offer initial migration or repair when a managed executable is missing."""
    if config.get("type") != "vyact" or not config.get("vyact_config", {}).get("model_path"):
        return []
    components = runtime_components(config)
    manifest = runtime_manifest()
    installed = installed_runtime()
    packages = []
    for component in components:
        if managed_executable(component):
            continue
        if platform.system() == "Linux" and component != "omlx":
            binary = "llama-server" if component == "llama.cpp" else "llama-swap"
            bundled = BUNDLED_RUNTIME_DIR / binary
            if installed.get(component, {}).get("version") and bundled.is_file() and os.access(bundled, os.X_OK):
                continue
        packages.append({"name": component, "installed": "", "available": manifest[component]["version"]})
    return packages


def runtime_version_direction(current: str, target: str) -> str:
    """Compare numeric release/build tags; never guess ordering for opaque tags."""
    versions = []
    for value in (current, target):
        match = re.fullmatch(r"(b|v)?(\d+(?:\.\d+)*)", value)
        if not match:
            return "change"
        family = "build" if match.group(1) == "b" else "release"
        numbers = [int(part) for part in match.group(2).split(".")]
        while len(numbers) > 1 and numbers[-1] == 0:
            numbers.pop()
        versions.append((family, tuple(numbers)))
    if versions[0][0] != versions[1][0] or versions[0][1] == versions[1][1]:
        return "change"
    return "downgrade" if versions[1][1] < versions[0][1] else "upgrade"


def pinned_updates(components: list[str]) -> list[dict]:
    """The version shipped with Vyact is the update target; consent is separate."""
    manifest = runtime_manifest()
    installed = installed_runtime()
    packages = []
    for component in components:
        target = manifest[component]["version"]
        current = installed.get(component, {}).get("version", "")
        if current != target:
            packages.append({"name": component, "installed": current, "available": target,
                             "direction": runtime_version_direction(current, target)})
    return packages


async def _download(asset: dict, destination: Path) -> None:
    logger.info("[runtime_install] download started asset=%s", asset["url"].split("?")[0])
    digest = hashlib.sha256()
    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        async with client.stream("GET", asset["url"]) as response:
            logger.info("[runtime_install] download HTTP status=%s", response.status_code)
            response.raise_for_status()
            with destination.open("wb") as output:
                async for chunk in response.aiter_bytes():
                    output.write(chunk)
                    digest.update(chunk)
    if digest.hexdigest() != asset["sha256"]:
        logger.error("[runtime_install] checksum mismatch expected=%s actual=%s", asset["sha256"], digest.hexdigest())
        raise RuntimeError("Runtime archive checksum mismatch")
    logger.info("[runtime_install] download verified bytes=%s", destination.stat().st_size)


def _extract(archive: Path, destination: Path) -> None:
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                target = (destination / member.filename).resolve()
                if destination.resolve() not in target.parents:
                    raise RuntimeError("Unsafe runtime archive path")
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise RuntimeError("Unexpected archive symlink")
            bundle.extractall(destination)
    else:
        with tarfile.open(archive) as bundle:
            bundle.extractall(destination, filter="data")


def runtime_environment(executable: Path) -> dict:
    environment = dict(os.environ)
    if platform.system() == "Linux":
        search = [str(executable.parent)]
        if environment.get("LD_LIBRARY_PATH"):
            search.append(environment["LD_LIBRARY_PATH"])
        environment["LD_LIBRARY_PATH"] = os.pathsep.join(search)
    return environment


def _extract_deb(archive: Path, destination: Path) -> None:
    """Read the data member of an official Debian ar archive without dpkg/root."""
    with archive.open("rb") as source:
        if source.read(8) != b"!<arch>\n":
            raise RuntimeError("Invalid runtime dependency archive")
        while header := source.read(60):
            if len(header) != 60 or header[58:] != b"`\n":
                raise RuntimeError("Invalid runtime dependency member")
            size = int(header[48:58].strip())
            contents = source.read(size)
            if len(contents) != size:
                raise RuntimeError("Truncated runtime dependency archive")
            if size % 2:
                source.read(1)
            if header[:16].decode().strip().rstrip("/").startswith("data.tar"):
                with tarfile.open(fileobj=io.BytesIO(contents)) as bundle:
                    bundle.extractall(destination, filter="data")
                return
    raise RuntimeError("Missing runtime dependency files")


async def _install_linux_dependencies(manifest: dict, temporary: Path, executable: Path) -> None:
    asset = manifest["linux_dependencies"][platform_key()]
    archive = temporary / "libgomp.deb"
    await _download(asset, archive)
    extracted = temporary / "libgomp"
    extracted.mkdir()
    _extract_deb(archive, extracted)
    libraries = list(extracted.rglob("libgomp.so.1"))
    if len(libraries) != 1:
        raise RuntimeError("Missing OpenMP runtime library")
    shutil.copy2(libraries[0], executable.parent / "libgomp.so.1")
    license_archive = temporary / "libgomp-license.deb"
    await _download(manifest["linux_dependency_license"], license_archive)
    _extract_deb(license_archive, extracted)
    licenses = executable.parent / "licenses" / "libgomp"
    licenses.mkdir(parents=True, exist_ok=True)
    copyright_file = extracted / "usr" / "share" / "doc" / "gcc-10-base" / "copyright"
    if not copyright_file.is_file():
        raise RuntimeError("Missing OpenMP license notice")
    shutil.copy2(copyright_file, licenses / "copyright")


def _publish(records: dict) -> None:
    record = {**installed_runtime(), **records}
    target = RUNTIME_ROOT / "installed-versions.json"
    temporary = target.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(record, output)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, target)


async def _cached_runtime(component: str, version: str) -> dict | None:
    """Probe retained installations; folder names alone do not prove the version."""
    root = RUNTIME_ROOT / "versions"
    name = {"llama.cpp": "llama-server", "llama-swap": "llama-swap", "omlx": "omlx"}[component]
    if platform.system() == "Windows":
        name += ".exe"
    for folder in sorted(root.glob(f"{component}-{version}-*")):
        if folder.is_symlink() or not folder.is_dir():
            continue
        matches = list(folder.rglob(name))
        if len(matches) != 1:
            continue
        executable = matches[0]
        if folder.resolve() not in executable.resolve().parents:
            continue
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                str(executable), "--version", stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT, env=runtime_environment(executable),
            )
            output, _ = await asyncio.wait_for(process.communicate(), timeout=15)
            # llama.cpp prints its numeric build, while swap/oMLX print release tags.
            numeric_version = version.lstrip("bv")
            pattern = rf"(?<![\w.])(?:[bv])?{re.escape(numeric_version)}(?![\w.])"
            if process.returncode == 0 and re.search(pattern, output.decode(errors="replace")):
                return {"version": version, "executable": str(executable.relative_to(RUNTIME_ROOT))}
        except (OSError, asyncio.TimeoutError):
            pass
        finally:
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
    return None


@protected("installation")
async def reuse_pinned_components(components: list[str]) -> None:
    """Select already installed release targets before asking to download anything."""
    async with _install_lock:
        manifest = runtime_manifest()
        current = installed_runtime()
        records = {}
        for component in components:
            version = manifest[component]["version"]
            if current.get(component, {}).get("version") == version and managed_executable(component):
                continue
            cached = await _cached_runtime(component, version)
            if cached:
                records[component] = cached
        if records:
            _publish(records)


@protected("installation")
async def install_pinned_components(components: list[str]) -> None:
    async with _install_lock:
        started = time.monotonic()
        component = ""
        stage = "prepare"
        logger.info("[runtime_install] started components=%s platform=%s os=%s python=%s", components, platform_key(), platform.release(), platform.python_version())
        records = {}
        created = []
        try:
            manifest = runtime_manifest()
            root = RUNTIME_ROOT / "versions"
            root.mkdir(parents=True, exist_ok=True)
            for component in components:
                stage = "cache_check"
                spec = manifest[component]
                logger.info("[runtime_install] component=%s target=%s", component, spec["version"])
                cached = await _cached_runtime(component, spec["version"])
                if cached:
                    logger.info("[runtime_install] cached runtime reused component=%s version=%s", component, spec["version"])
                    records[component] = cached
                    continue
                folder = root / f"{component}-{spec['version']}-{uuid.uuid4().hex}"
                folder.mkdir()
                created.append(folder)
                if component == "omlx":
                    if platform_key() != "Darwin-arm64":
                        raise RuntimeError("oMLX requires Apple Silicon")
                    macos_version = platform.mac_ver()[0]
                    if macos_version and int(macos_version.split(".")[0]) < 15:
                        raise RuntimeError("Pinned oMLX requires macOS 15 or newer")
                    python_tag = f"{sys.version_info.major}{sys.version_info.minor}"
                    asset = spec["assets"].get(python_tag)
                else:
                    asset = spec["assets"].get(platform_key())
                if not asset:
                    raise RuntimeError(f"No pinned {component} package for this platform")
                with tempfile.TemporaryDirectory(dir=root) as temporary:
                    archive = Path(temporary) / asset["url"].rsplit("/", 1)[-1]
                    bundle_spec = _read_records(BUNDLED_RUNTIME_DIR / "runtime-versions.json").get(component, {})
                    use_bundle = platform.system() == "Linux" and bundle_spec.get("version") == spec["version"]
                    stage = "download"
                    if not use_bundle:
                        await _download(asset, archive)
                    stage = "install_or_extract"
                    if component == "omlx":
                        python = folder / "bin" / "python"
                        commands = [
                            [sys.executable, "-m", "venv", str(folder)],
                            [str(python), "-m", "pip", "install", str(archive)],
                        ]
                        for command in commands:
                            if await run_install_command(command, get_log_file("event")):
                                raise RuntimeError("Pinned oMLX installation failed")
                        executable = folder / "bin" / "omlx"
                    else:
                        if use_bundle:
                            shutil.copytree(BUNDLED_RUNTIME_DIR, folder, dirs_exist_ok=True)
                        else:
                            _extract(archive, folder)
                        name = "llama-server" if component == "llama.cpp" else "llama-swap"
                        if platform.system() == "Windows":
                            name += ".exe"
                        matches = list(folder.rglob(name))
                        if len(matches) != 1:
                            raise RuntimeError(f"Expected exactly one {name} in runtime archive")
                        executable = matches[0]
                        executable.chmod(executable.stat().st_mode | 0o111)
                        if platform.system() == "Linux" and component == "llama.cpp" and not use_bundle:
                            stage = "linux_dependencies"
                            await _install_linux_dependencies(manifest, Path(temporary), executable)
                stage = "executable_check"
                if not executable.is_file():
                    raise RuntimeError(f"Missing installed executable for {component}")
                if await run_install_command([str(executable), "--version"], get_log_file("event"), env=runtime_environment(executable)):
                    raise RuntimeError(f"Pinned {component} executable failed its startup check")
                records[component] = {"version": spec["version"], "executable": str(executable.relative_to(RUNTIME_ROOT))}
            stage = "activate"
            _publish(records)
            logger.info("[runtime_install] completed components=%s elapsed=%.2fs", components, time.monotonic() - started)
        except BaseException:
            logger.exception("[runtime_install] failed component=%s stage=%s elapsed=%.2fs; previous active runtime preserved", component, stage, time.monotonic() - started)
            for folder in created:
                shutil.rmtree(folder, ignore_errors=True)
            raise
