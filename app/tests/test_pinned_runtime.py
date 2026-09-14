import asyncio
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from services import pinned_runtime as runtime


class PinnedRuntimeTests(unittest.TestCase):
    def test_manifest_contains_only_versioned_assets_with_checksums(self):
        manifest = runtime.runtime_manifest()
        self.assertNotIn('reviewed_platforms', manifest)
        for name in ('llama.cpp', 'llama-swap', 'omlx'):
            for asset in manifest[name]['assets'].values():
                self.assertNotIn('latest', asset['url'])
                self.assertIn('/releases/download/', asset['url'])
                self.assertEqual(len(asset['sha256']), 64)

    def test_pin_change_alone_offers_update_without_review_metadata(self):
        for target, expected in [("v1", False), ("v2", True)]:
            with patch.object(runtime, "runtime_manifest", return_value={"omlx": {"version": target}}), \
                 patch.object(runtime, "installed_runtime", return_value={"omlx": {"version": "v1"}}):
                self.assertEqual(bool(runtime.pinned_updates(["omlx"])), expected)

    def test_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr('../escape', 'bad')
            with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
                runtime._extract(archive, root / 'output')
            self.assertFalse((root / 'escape').exists())

    def test_publication_is_atomic_on_success_failure_and_cancellation(self):
        for failure in (None, RuntimeError('checksum mismatch'), asyncio.CancelledError()):
            async def download(asset, target):
                if 'swap' in asset['url'] and failure is not None:
                    raise failure
                name = 'llama-swap' if 'swap' in asset['url'] else 'llama-server'
                with zipfile.ZipFile(target, 'w') as bundle:
                    bundle.writestr('bin/' + name, 'binary')
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                previous = {'llama.cpp': {'version': 'old', 'executable': 'old/bin'}}
                (root / 'installed-versions.json').write_text(json.dumps(previous))
                with patch.object(runtime, 'RUNTIME_ROOT', root), \
                     patch.object(runtime, 'platform_key', return_value='Darwin-arm64'), \
                     patch.object(runtime.platform, 'system', return_value='Darwin'), \
                     patch.object(runtime, '_download', side_effect=download), \
                     patch.object(runtime, 'run_install_command', new=AsyncMock(return_value=0)):
                    if failure is not None:
                        with self.assertRaises(type(failure)):
                            asyncio.run(runtime.install_pinned_components(['llama.cpp', 'llama-swap']))
                        self.assertEqual(runtime.installed_runtime(), previous)
                        self.assertEqual(list((root / 'versions').iterdir()), [])
                    else:
                        asyncio.run(runtime.install_pinned_components(['llama.cpp', 'llama-swap']))
                        self.assertEqual(runtime.installed_runtime()['llama.cpp']['version'], 'b10809')
                        self.assertEqual(runtime.managed_executable('llama-swap').name, 'llama-swap')

    def test_download_rejects_wrong_checksum(self):
        class Response:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            def raise_for_status(self): pass
            async def aiter_bytes(self): yield b'wrong bytes'
        class Client(Response):
            def stream(self, *args): return Response()
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(runtime.httpx, 'AsyncClient', return_value=Client()):
            with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                asyncio.run(runtime._download({'url': 'https://example.test', 'sha256': '0' * 64}, Path(directory) / 'archive'))

    def test_existing_external_runtimes_need_migration_on_macos_and_windows(self):
        for system, key in [("Darwin", "Darwin-arm64"), ("Windows", "Windows-x86_64")]:
            with self.subTest(system=system), \
                 patch.object(runtime.platform, "system", return_value=system), \
                 patch.object(runtime, "platform_key", return_value=key), \
                 patch.object(runtime, "managed_executable", return_value=None), \
                 patch.object(runtime, "omlx_executable", return_value="/opt/homebrew/bin/omlx"), \
                 patch.object(runtime, "installed_runtime", return_value={}):
                packages = runtime.migration_packages({"type": "vyact", "vyact_config": {"model_path": "model.gguf"}})
            self.assertEqual([item["name"] for item in packages],
                             ["llama.cpp", "llama-swap", "omlx"] if system == "Darwin" else ["llama.cpp", "llama-swap"])

    def test_completed_managed_install_does_not_repeat_migration(self):
        with patch.object(runtime, "managed_executable", return_value=Path("/managed/binary")):
            packages = runtime.migration_packages({"type": "vyact", "vyact_config": {"model_path": "model.gguf"}})
        self.assertEqual(packages, [])

    def test_remote_provider_does_not_download_unused_local_runtimes(self):
        self.assertEqual(runtime.migration_packages({"type": "openai"}), [])

    def test_bundled_linux_install_does_not_need_migration(self):
        with patch.object(runtime.platform, "system", return_value="Linux"), \
             patch.object(runtime, "platform_key", return_value="Linux-x86_64"), \
             patch.object(runtime, "managed_executable", return_value=None), \
             patch.object(runtime, "installed_runtime", return_value={"llama.cpp": {"version": "b10809"}, "llama-swap": {"version": "v255"}}), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(runtime.os, "access", return_value=True):
            self.assertEqual(runtime.migration_packages({"type": "vyact", "vyact_config": {"model_path": "model.gguf"}}), [])

    def test_old_copied_bundle_metadata_does_not_override_new_bundle_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "runtime-versions.json").write_text(json.dumps({"llama.cpp": {"version": "b2"}}))
            (root / "installed-versions.json").write_text(json.dumps({"llama.cpp": {"version": "b1"}}))
            with patch.object(runtime, "RUNTIME_ROOT", root), \
                 patch.object(runtime, "BUNDLED_RUNTIME_DIR", bundle), \
                 patch.object(runtime.platform, "system", return_value="Linux"):
                self.assertEqual(runtime.installed_runtime()["llama.cpp"]["version"], "b2")

    def test_linux_environment_points_to_private_libraries(self):
        with patch.object(runtime.platform, "system", return_value="Linux"):
            environment = runtime.runtime_environment(Path("/private/runtime/llama-server"))
        self.assertEqual(environment["LD_LIBRARY_PATH"].split(":")[0], "/private/runtime")

    def test_upgrade_and_downgrade_compare_numbers_instead_of_strings(self):
        for current, target, expected in [
            ("b10956", "b10809", "downgrade"),
            ("v255", "v253", "downgrade"),
            ("v0.6.10", "v0.6.4", "downgrade"),
            ("v0.6.4", "v0.6.10", "upgrade"),
            ("b9999", "b10000", "upgrade"),
            ("v0.6", "v0.6.0", "change"),
            ("custom-build", "v255", "change"),
            ("b10809", "v0.4.0", "change"),
        ]:
            with self.subTest(current=current, target=target):
                self.assertEqual(runtime.runtime_version_direction(current, target), expected)

    def test_older_app_pin_offers_downgrade_with_both_versions(self):
        with patch.object(runtime, "runtime_manifest", return_value={"omlx": {"version": "v0.6.3"}}), \
             patch.object(runtime, "installed_runtime", return_value={"omlx": {"version": "v0.6.4"}}):
            self.assertEqual(runtime.pinned_updates(["omlx"]), [{
                "name": "omlx", "installed": "v0.6.4", "available": "v0.6.3", "direction": "downgrade",
            }])

    def test_downgrade_switches_active_record_without_deleting_newer_runtime(self):
        async def download(asset, target):
            with zipfile.ZipFile(target, "w") as bundle:
                bundle.writestr("llama-swap", "older runtime")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous_binary = root / "versions" / "newer" / "llama-swap"
            previous_binary.parent.mkdir(parents=True)
            previous_binary.write_text("newer runtime")
            (root / "installed-versions.json").write_text(json.dumps({
                "llama-swap": {"version": "v256", "executable": str(previous_binary.relative_to(root))},
            }))
            with patch.object(runtime, "RUNTIME_ROOT", root), \
                 patch.object(runtime, "platform_key", return_value="Darwin-arm64"), \
                 patch.object(runtime.platform, "system", return_value="Darwin"), \
                 patch.object(runtime, "_download", side_effect=download), \
                 patch.object(runtime, "run_install_command", new=AsyncMock(return_value=0)):
                asyncio.run(runtime.install_pinned_components(["llama-swap"]))
                self.assertEqual(runtime.installed_runtime()["llama-swap"]["version"], "v255")
                self.assertEqual(runtime.managed_executable("llama-swap").read_text(), "older runtime")
                self.assertEqual(previous_binary.read_text(), "newer runtime")
