import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import es_native


class NativeElasticsearchPlatformTests(unittest.TestCase):
    def test_native_heap_matches_desktop_docker_budget(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "config").mkdir()
            with patch.object(es_native, "ES_HOME", root), \
                 patch.object(es_native, "ES_DATA", root / "data"), \
                 patch.object(es_native, "ES_LOGS", root / "logs"):
                es_native._write_es_config()
            options = (root / "config/jvm.options.d/vyact.options").read_text()
            compose = (Path(__file__).parents[1] / "docker-compose.yml").read_text()
            for option in options.splitlines():
                self.assertIn(option, compose)

    def test_detects_linux_x86_64(self):
        with patch("services.es_native.platform.system", return_value="Linux"), \
             patch("services.es_native.platform.machine", return_value="x86_64"):
            self.assertEqual(es_native.detect_platform(), "linux-x86_64")

    def test_rejects_unsupported_linux_architecture(self):
        with patch("services.es_native.platform.system", return_value="Linux"), \
             patch("services.es_native.platform.machine", return_value="riscv64"):
            self.assertIsNone(es_native.detect_platform())



if __name__ == "__main__":
    unittest.main()
