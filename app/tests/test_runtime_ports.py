import asyncio
import socket
import unittest
from unittest.mock import AsyncMock, patch
from services import runtime_ports as ports
from services.llm.config import get_provider_config
from services.runtime_error_details import RuntimeStartupError


class RuntimePortsTests(unittest.TestCase):
    def test_occupied_port_is_avoided_without_touching_listener(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            occupied = listener.getsockname()[1]
            self.assertNotEqual(ports._free_port(occupied, set()), occupied)
            with socket.create_connection(('127.0.0.1', occupied), timeout=1):
                pass

    def test_bind_race_retries_both_ports_and_updates_url(self):
        attempts = []
        @ports.with_runtime_ports
        def launch():
            attempts.append((ports.get_runtime_port(), ports.get_model_port(), ports.get_runtime_url()))
            if len(attempts) == 1:
                raise RuntimeStartupError('failed', 'bind: address already in use')
            return 'ready'
        with patch.object(ports, '_free_port', side_effect=[21001, 21002, 21003, 21004]), \
             patch.object(ports, '_runtime_port', ports.DEFAULT_RUNTIME_PORT), \
             patch.object(ports, '_model_port', ports.DEFAULT_MODEL_PORT):
            self.assertEqual(launch(), 'ready')
        self.assertEqual(attempts, [(21001, 21002, 'http://127.0.0.1:21001/v1'),
                                    (21003, 21004, 'http://127.0.0.1:21003/v1')])

    def test_only_bind_errors_are_retried_and_retries_are_bounded(self):
        for message, expected in [('out of memory', 1), ('address already in use', ports.MAX_PORT_ATTEMPTS)]:
            calls = []
            @ports.with_runtime_ports
            def launch():
                calls.append(True)
                raise RuntimeError(message)
            with patch.object(ports, '_free_port', return_value=21001), \
                 patch.object(ports, '_runtime_port', ports.DEFAULT_RUNTIME_PORT), \
                 patch.object(ports, '_model_port', ports.DEFAULT_MODEL_PORT):
                with self.assertRaises(RuntimeError):
                    launch()
            self.assertEqual(len(calls), expected)

    def test_provider_uses_current_port_instead_of_saved_endpoint(self):
        saved = {"type": "vyact", "model": "test", "vyact_config": {"base_url": "http://127.0.0.1:11435/v1"}}
        with patch("routers.deps.load_config_async", new=AsyncMock(return_value=saved)), \
             patch.object(ports, "_runtime_port", 21999):
            self.assertEqual(asyncio.run(get_provider_config())["base_url"], "http://127.0.0.1:21999/v1")
