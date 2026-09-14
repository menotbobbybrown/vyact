import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from services import es_native
from services.installer import Installer


class InstallationLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_setup_uses_same_desktop_lifecycle(self):
        with patch.object(es_native, 'ElasticsearchLifecycle') as factory:
            await es_native._start_es_background()
        factory.assert_called_once_with(es_native.INSTALL_DIR, es_native.ES_PORT)
        factory.return_value.start_native.assert_called_once_with(es_native.ES_HOME)

    async def test_docker_setup_records_new_container_for_desktop_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installer = Installer(root, root, root, root/'install.log')
            container = {'Id': 'new-container', 'State': {'Running': True, 'StartedAt': 'now'}}
            process = AsyncMock(); process.returncode = 0
            with patch('services.installer.ElasticsearchLifecycle') as factory, patch.object(installer, '_run', AsyncMock(return_value=0)), patch('services.installer.asyncio.sleep', AsyncMock()), patch('services.installer.asyncio.create_subprocess_exec', AsyncMock(return_value=process)):
                factory.return_value.docker_container.side_effect = [None, container]
                result = await installer.start_elasticsearch()
            self.assertTrue(result[0])
            factory.return_value.select.assert_called_once_with('docker')
            factory.return_value.record_owner.assert_called_once_with(mode='docker', id='new-container', started_at='now')

    async def test_failed_compose_does_not_record_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installer = Installer(root, root, root, root/'install.log')
            with patch('services.installer.ElasticsearchLifecycle') as factory, patch.object(installer, '_run', AsyncMock(return_value=1)):
                factory.return_value.docker_container.return_value = None
                result = await installer.start_elasticsearch()
            self.assertFalse(result[0])
            factory.return_value.record_owner.assert_not_called()
