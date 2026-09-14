import copy
import json
import os
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from services.es_lifecycle import ElasticsearchLifecycle, read_json, stop_windows_console


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.service = ElasticsearchLifecycle(self.root, session='session')
        self.container = {'Id': 'cid', 'State': {'Running': False, 'StartedAt': 'start'},
            'Config': {'Labels': {'com.docker.compose.project': 'vyact', 'com.docker.compose.service': 'elasticsearch'}},
            'HostConfig': {'RestartPolicy': {'Name': 'always'}, 'PortBindings': {'9200/tcp': [{'HostPort': '9251'}]}}}

    def native(self, version='9.4.5'):
        home = self.root / f'elasticsearch-{version}'
        (home / 'bin').mkdir(parents=True)
        (home / 'bin/elasticsearch').touch()
        (home / 'config').mkdir()
        (home / 'config/elasticsearch.yml').write_text('path.data: persistent-data')
        (home / '.vyact_install_complete').touch()
        return home

    def test_docker_migration_and_start_preserve_container(self):
        with patch.object(self.service, 'ready', return_value=False), patch.object(self.service, 'docker_container', return_value=self.container), patch('services.es_lifecycle.run', side_effect=['updated', 'started', json.dumps([self.container])]) as run:
            self.service.start()
        self.assertEqual(run.call_args_list[0].args[0], ['docker', 'update', '--restart', 'on-failure:3', 'cid'])
        self.assertEqual(run.call_args_list[1].args[0], ['docker', 'start', 'cid'])
        self.assertEqual(read_json(self.service.selection_file), {'mode': 'docker'})
        self.assertEqual(read_json(self.service.owner_file)['id'], 'cid')

    def test_running_docker_migrates_without_adoption(self):
        self.container['State']['Running'] = True
        with patch.object(self.service, 'ready', return_value=True), patch.object(self.service, 'request', side_effect=RuntimeError), patch.object(self.service, 'docker_container', return_value=self.container), patch('services.es_lifecycle.run') as run:
            self.service.start()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][1], 'update')
        self.assertFalse(self.service.owner_file.exists())

    def test_saved_docker_never_falls_back_to_native(self):
        self.native(); self.service.select('docker')
        with patch.object(self.service, 'ready', return_value=False), patch.object(self.service, 'docker_container', side_effect=RuntimeError('offline')), patch.object(self.service, 'start_native') as start:
            with self.assertRaises(RuntimeError): self.service.start()
        start.assert_not_called()
        self.assertEqual(read_json(self.service.selection_file)['mode'], 'docker')

    def test_ambiguous_installations_fail_closed(self):
        self.native()
        with self.assertRaises(RuntimeError): self.service.discover(False, self.container)
        self.assertFalse(self.service.selection_file.exists())

    def test_saved_native_uses_original_version(self):
        home = self.native(); self.native('9.5.0'); self.service.select('native', home)
        with patch.object(self.service, 'ready', return_value=False), patch.object(self.service, 'docker_container') as docker, patch.object(self.service, 'remove_legacy_autostart'), patch.object(self.service, 'start_native') as start:
            self.service.start()
        docker.assert_not_called(); start.assert_called_once_with(str(home))

    def test_running_native_is_identified_by_server_path(self):
        home = self.native()
        with patch.object(self.service, 'request', return_value={'nodes': {'node': {'settings': {'path': {'home': str(home)}}}}}):
            self.assertEqual(self.service.discover(True, None)['home'], str(home))

    def test_external_server_not_adopted(self):
        with patch.object(self.service, 'request', side_effect=RuntimeError):
            self.assertIsNone(self.service.discover(True, None))
        self.assertFalse(self.service.selection_file.exists())

    def test_missing_selected_native_not_replaced(self):
        self.native('9.5.0')
        with self.assertRaises(RuntimeError): self.service.start_native(self.root / 'elasticsearch-9.4.5')

    def test_incomplete_native_is_not_started(self):
        home = self.native(); (home / '.vyact_install_complete').unlink()
        self.assertEqual(self.service.native_homes(), [])

    def test_first_setup_opens_but_completed_setup_requires_es(self):
        with patch.object(self.service, 'ready', return_value=False), patch.object(self.service, 'docker_container', return_value=None):
            self.service.start()
            (self.root / '.setup_done').touch()
            with self.assertRaises(RuntimeError): self.service.start()

    def test_autostart_migration_only_removes_matching_entry(self):
        home = self.native()
        for system, relative in [('linux', 'config/autostart/vyact-elasticsearch.desktop'), ('darwin', 'Library/LaunchAgents/com.vyact.elasticsearch.plist'), ('win32', 'appdata/Microsoft/Windows/Start Menu/Programs/Startup/vyact-elasticsearch.vbs')]:
            with self.subTest(system=system), patch('services.es_lifecycle.sys.platform', system), patch('services.es_lifecycle.Path.home', return_value=self.root), patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.root/'config'), 'APPDATA': str(self.root/'appdata')}):
                entry = self.root / relative; entry.parent.mkdir(parents=True, exist_ok=True)
                entry.write_text('/unrelated/elasticsearch/bin/elasticsearch')
                self.service.remove_legacy_autostart(home); self.assertTrue(entry.exists())
                entry.write_text(str(home / 'bin' / ('elasticsearch.bat' if system == 'win32' else 'elasticsearch')))
                self.service.remove_legacy_autostart(home); self.assertFalse(entry.exists())
                self.assertTrue((home/'config/elasticsearch.yml').exists())

    def test_other_session_is_not_stopped(self):
        self.service.session = 'old'; self.service.record_owner(mode='docker', id='cid', started_at='start'); self.service.session = 'session'
        with patch('services.es_lifecycle.run') as run: self.service.stop()
        run.assert_not_called()

    def test_owned_container_is_stopped_not_deleted(self):
        self.service.record_owner(mode='docker', id='cid', started_at='start')
        with patch.object(self.service, 'docker_container', return_value=self.container), patch('services.es_lifecycle.run') as run:
            self.service.stop()
        run.assert_called_once_with(['docker', 'stop', '--time', '30', 'cid'], timeout=40)
        self.assertFalse(self.service.owner_file.exists())

    def test_recreated_or_restarted_container_is_preserved(self):
        for field in ['id', 'started_at']:
            owner = {'mode': 'docker', 'id': 'cid', 'started_at': 'start'}; owner[field] = 'other'
            self.service.record_owner(**owner)
            with patch.object(self.service, 'docker_container', return_value=self.container), patch('services.es_lifecycle.run') as run: self.service.stop()
            run.assert_not_called()

    def test_reused_native_pid_is_preserved(self):
        self.service.record_owner(mode='native', pid=12345, created='old', home='/original/home')
        with patch.object(self.service, 'process_identity', return_value=('new', '/original/home')), patch('services.es_lifecycle.os.kill') as kill: self.service.stop()
        kill.assert_not_called()

    def test_owned_native_gets_graceful_signal(self):
        self.service.record_owner(mode='native', pid=12345, created='old', home='/original/home')
        with patch.object(self.service, 'process_identity', side_effect=[('old', '/original/home/bin/elasticsearch'), OSError()]), patch('services.es_lifecycle.os.kill') as kill: self.service.stop()
        kill.assert_called_once_with(12345, signal.SIGTERM)

    def test_container_name_alone_is_not_ownership(self):
        self.container['Config']['Labels'] = {}
        with patch('services.es_lifecycle.shutil.which', return_value='/docker'), patch('services.es_lifecycle.run', side_effect=['version', 'cid', json.dumps([self.container])]):
            self.assertIsNone(self.service.docker_container())

    def test_migration_failure_preserves_running_service(self):
        self.service.select('docker')
        with patch.object(self.service, 'ready', return_value=True), patch.object(self.service, 'docker_container', return_value=self.container), patch.object(self.service, 'migrate', side_effect=PermissionError('denied')):
            self.service.start()
        self.assertFalse(self.service.owner_file.exists())

    def test_identity_failure_cleans_up_just_started_process(self):
        home = self.native()
        with patch.object(self.service, 'ready', return_value=False), patch.object(self.service, 'remove_legacy_autostart'), patch.object(self.service, 'process_identity', side_effect=PermissionError('blocked')), patch('services.es_lifecycle.subprocess.Popen') as popen:
            process = popen.return_value
            process.poll.return_value = None
            with self.assertRaises(PermissionError): self.service.start_native(home)
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=30)
        self.assertFalse(self.service.owner_file.exists())

    def test_windows_shutdown_uses_only_attached_private_console(self):
        with patch('services.es_lifecycle.ctypes.WinDLL', create=True) as library:
            kernel = library.return_value
            stop_windows_console(123)
            kernel.GenerateConsoleCtrlEvent.assert_called_once_with(0, 0)
            self.assertEqual(kernel.AttachConsole.call_args.args[0].value, 123)
            self.assertEqual(kernel.FreeConsole.call_count, 2)
            kernel.SetConsoleCtrlHandler.assert_called_once_with(None, True)

    def test_windows_failed_console_attach_does_not_signal(self):
        with patch('services.es_lifecycle.ctypes.WinDLL', create=True) as library, patch('services.es_lifecycle.ctypes.WinError', return_value=OSError('denied'), create=True), patch('services.es_lifecycle.ctypes.get_last_error', return_value=5, create=True):
            kernel = library.return_value
            kernel.AttachConsole.return_value = 0
            with self.assertRaises(OSError): stop_windows_console(123)
            kernel.GenerateConsoleCtrlEvent.assert_not_called()

    def test_slow_native_start_is_not_duplicated_by_setup(self):
        home = self.native()
        self.service.record_owner(mode='native', pid=12345, created='same', home=str(home))
        with patch.object(self.service, 'ready', return_value=False), patch.object(self.service, 'remove_legacy_autostart'), patch.object(self.service, 'process_identity', return_value=('same', str(home/'bin/elasticsearch'))), patch('services.es_lifecycle.subprocess.Popen') as popen:
            self.service.start_native(home)
        popen.assert_not_called()
