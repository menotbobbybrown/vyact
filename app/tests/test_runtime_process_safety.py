import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import psutil
from services import vyact_runtime as runtime


class RuntimeProcessSafetyTests(unittest.TestCase):
    def test_liveness_check_never_sends_a_signal(self):
        process = Mock()
        process.is_running.return_value = True
        process.status.return_value = psutil.STATUS_RUNNING
        with patch.object(runtime, '_runtime_process', None), \
             patch.object(runtime.psutil, 'Process', return_value=process), \
             patch.object(runtime.os, 'kill') as kill:
            self.assertFalse(runtime._process_has_exited(1234))
        kill.assert_not_called()

    def test_identity_requires_our_configuration_and_does_not_use_wmic(self):
        for config, expected in [(str(runtime.VYACT_SWAP_CONFIG), True), ('/other/config.yaml', False)]:
            with patch.object(runtime.psutil, 'Process', return_value=Mock(cmdline=Mock(return_value=['C:\\Runtime\\llama-swap.exe', '--config', config]))), \
                 patch.object(runtime.subprocess, 'check_output') as subprocess:
                self.assertEqual(runtime._is_llama_swap_process(1234), expected)
            subprocess.assert_not_called()

    def test_reaped_and_missing_processes_are_detected_without_signals(self):
        with patch.object(runtime, '_runtime_process', Mock(pid=1234, poll=Mock(return_value=0))):
            self.assertTrue(runtime._process_has_exited(1234))
        with patch.object(runtime, '_runtime_process', None), \
             patch.object(runtime.psutil, 'Process', side_effect=psutil.NoSuchProcess(1234)):
            self.assertTrue(runtime._process_has_exited(1234))

    def test_windows_stop_terminates_owned_children_before_parent(self):
        events = []
        child = Mock()
        child.terminate.side_effect = lambda: events.append('child')
        parent = Mock()
        parent.children.return_value = [child]
        parent.terminate.side_effect = lambda: events.append('parent')
        with patch.object(runtime, '_runtime_process', None), \
             patch.object(runtime, '_read_owned_pid', return_value=1234), \
             patch.object(runtime, '_is_llama_swap_process', return_value=True), \
             patch.object(runtime, '_process_has_exited', side_effect=[False, True]), \
             patch.object(runtime, 'VYACT_RUNTIME_PID_FILE', Mock()), \
             patch.object(runtime.psutil, 'Process', return_value=parent), \
             patch.object(runtime.os, 'name', 'nt'), \
             patch.object(runtime.os, 'kill') as kill:
            runtime.stop_runtime()
        self.assertEqual(events, ['child', 'parent'])
        child.wait.assert_called_once_with(timeout=10)
        kill.assert_not_called()
