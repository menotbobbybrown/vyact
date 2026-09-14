"""Desktop-owned Elasticsearch lifecycle. Standard library only: runs before FastAPI.

Never recreate a container, switch stores, delete data, or adopt a running process.
The session token is supplied by Electron and inherited by the setup backend.
"""
import ctypes
import json
import os
import signal
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CONTAINER = 'vyact-es'
RESTART_POLICY = 'on-failure:3'
SESSION_ENV = 'VYACT_ES_SESSION'


class DockerUnavailableError(RuntimeError):
    """The desktop may retry while Docker Desktop is starting at login."""



def run(args, timeout=15):
    return subprocess.check_output(args, text=True, encoding='utf-8', errors='replace', stderr=subprocess.STDOUT, timeout=timeout,
                                   **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {})).strip()


def read_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    temporary.replace(path)


def stop_windows_console(pid):
    """Send Ctrl+C only to the private hidden console created for this ES."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.FreeConsole()
    if not kernel.AttachConsole(ctypes.c_uint(pid)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not kernel.SetConsoleCtrlHandler(None, True):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.GenerateConsoleCtrlEvent(0, 0):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.FreeConsole()



class ElasticsearchLifecycle:
    def __init__(self, root, port=9251, session=None):
        self.original_root = Path(root).absolute()
        self.root = Path(root).resolve()
        self.port = int(port)
        self.session = session or os.environ.get(SESSION_ENV)
        self.selection_file = self.root / 'es-runtime.json'
        self.owner_file = self.root / 'es-runtime-owner.json'

    def request(self, endpoint=''):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{self.port}/{endpoint}', timeout=2) as response:
            return json.load(response)

    def ready(self):
        try:
            return bool(self.request().get('cluster_name'))
        except Exception:
            return False

    def docker_container(self):
        if shutil.which('docker') is None:
            return None
        try:
            # A stopped daemon is not proof that a Docker installation is absent.
            run(['docker', 'info', '--format', '{{.ServerVersion}}'])
            ids = run(['docker', 'ps', '-aq', '--filter', f'name=^/{CONTAINER}$'])
            if not ids:
                return None
            data = json.loads(run(['docker', 'inspect', CONTAINER]))[0]
            labels = data.get('Config', {}).get('Labels') or {}
            ports = data.get('HostConfig', {}).get('PortBindings') or {}
            owned = labels.get('com.docker.compose.service') == 'elasticsearch'
            owned = owned and labels.get('com.docker.compose.project') == 'vyact'
            owned = owned and any(binding.get('HostPort') == str(self.port) for binding in ports.get('9200/tcp', []) or [])
            return data if owned else None
        except (OSError, subprocess.SubprocessError) as error:
            raise DockerUnavailableError('Docker is unavailable; the existing storage mode will not be changed.') from error

    def native_homes(self):
        binary = 'elasticsearch.bat' if os.name == 'nt' else 'elasticsearch'
        return [home for home in self.root.glob('elasticsearch-*')
                if (home / 'bin' / binary).is_file() and (home / 'config/elasticsearch.yml').is_file()
                and ((home / '.vyact_install_complete').exists() or (self.root / '.setup_done').exists())]

    def select(self, mode, home=None):
        selection = {'mode': mode}
        if home:
            home = Path(home).resolve()
            if home not in self.native_homes():
                raise RuntimeError('Native Elasticsearch installation does not match the managed directory.')
            selection['home'] = str(home)
        write_json(self.selection_file, selection)
        return selection

    def remove_legacy_autostart(self, home):
        # Only remove our named entry when it points to this installation.
        if sys.platform == 'win32':
            appdata = os.environ.get('APPDATA')
            if not appdata:
                return
            entry = Path(appdata) / 'Microsoft/Windows/Start Menu/Programs/Startup/vyact-elasticsearch.vbs'
        elif sys.platform == 'darwin':
            entry = Path.home() / 'Library/LaunchAgents/com.vyact.elasticsearch.plist'
        else:
            entry = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'autostart/vyact-elasticsearch.desktop'
        if entry.is_file() and str(Path(home) / 'bin' / ('elasticsearch.bat' if sys.platform == 'win32' else 'elasticsearch')) in entry.read_text(encoding='utf-8').replace(str(self.original_root), str(self.root)):
            entry.unlink()

    def migrate(self, selection, container=None):
        if selection['mode'] == 'native':
            self.remove_legacy_autostart(selection['home'])
        elif selection['mode'] == 'docker':
            container = container or self.docker_container()
            if not container:
                raise RuntimeError('The existing Vyact Elasticsearch container is missing.')
            policy = container.get('HostConfig', {}).get('RestartPolicy', {})
            if policy.get('Name') != 'on-failure' or policy.get('MaximumRetryCount') != 3:
                run(['docker', 'update', '--restart', RESTART_POLICY, container['Id']])

    def discover(self, ready, container):
        homes = self.native_homes()
        if ready:
            # Identify the server actually responding, not just an installed binary.
            try:
                nodes = self.request('_nodes/settings').get('nodes', {}).values()
                paths = {str(Path(value).resolve()) for node in nodes
                         if isinstance(value := node.get('settings', {}).get('path', {}).get('home'), str)}
                matches = [home for home in homes if str(home) in paths]
                if len(matches) == 1:
                    return self.select('native', matches[0])
            except Exception:
                pass
            if container and container['State']['Running']:
                return self.select('docker')
            return None  # Externally managed ES: leave it alone.
        if container and not homes:
            return self.select('docker')
        if len(homes) == 1 and not container:
            return self.select('native', homes[0])
        if homes or container:
            raise RuntimeError('Multiple Elasticsearch installations found; refusing to select a different data store.')
        return None

    def record_owner(self, **identity):
        if self.session:
            write_json(self.owner_file, {'session': self.session, **identity})

    def process_identity(self, pid):
        if os.name == 'nt':
            script = f'[Console]::OutputEncoding = [Text.UTF8Encoding]::new(); Get-CimInstance Win32_Process -Filter "ProcessId={int(pid)}" | Select-Object CreationDate,CommandLine | ConvertTo-Json -Compress'
            data = json.loads(run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script]))
            return data['CreationDate'], data['CommandLine']
        return (run(['ps', '-p', str(pid), '-o', 'lstart=']),
                run(['ps', '-p', str(pid), '-o', 'command=']))

    def start_native(self, home):
        home = Path(home).resolve()
        self.select('native', home)
        try:
            self.remove_legacy_autostart(home)
        except OSError as error:
            print(f'Elasticsearch autostart migration will be retried: {error}', file=sys.stderr)
        if self.ready():
            return
        existing = read_json(self.owner_file)
        if existing and existing.get('mode') == 'native' and existing.get('home') == str(home):
            try:
                created, command = self.process_identity(int(existing['pid']))
                if created == existing.get('created') and str(home) in command:
                    return  # A previous launch is still warming up; don't spawn a second JVM.
            except subprocess.CalledProcessError as error:
                if error.returncode != 1:
                    raise
            except (TypeError, json.JSONDecodeError):
                pass  # Windows reports null for an exited process.
        binary = home / 'bin' / ('elasticsearch.bat' if os.name == 'nt' else 'elasticsearch')
        if os.name != 'nt':
            binary.chmod(binary.stat().st_mode | 0o100)
        args = [str(binary)]
        options = {'start_new_session': True}
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            options = {'creationflags': subprocess.CREATE_NEW_CONSOLE, 'startupinfo': startupinfo}
        if os.name == 'nt':
            args = subprocess.list2cmdline([os.environ.get('COMSPEC', 'cmd.exe')]) + f' /d /s /c ""{binary}""'
        logs = self.root / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / 'elasticsearch-launcher.log').open('ab') as output:
            process = subprocess.Popen(args, cwd=home, stdin=subprocess.DEVNULL, stdout=output, stderr=output, **options)
        # Creation time survives the Unix launcher's exec(java), unlike its initial command line.
        try:
            created, _ = self.process_identity(process.pid)
            self.record_owner(mode='native', pid=process.pid, created=created, home=str(home))
        except Exception:
            # We still hold the process handle here: clean up a launch whose
            # identity/ownership could not be recorded, never an unrelated PID.
            if process.poll() is None:
                if os.name == 'nt':
                    stop_windows_console(process.pid)
                else:
                    process.terminate()
                process.wait(timeout=30)
            raise

    def start(self):
        selection = read_json(self.selection_file)
        ready = self.ready()
        container = None
        docker_unavailable = False
        if not selection or selection.get('mode') == 'docker':
            try:
                container = self.docker_container()
            except RuntimeError:
                docker_unavailable = True
                if selection and selection.get('mode') == 'docker' and not ready:
                    raise
        if not selection:
            if docker_unavailable and not ready and self.native_homes():
                raise DockerUnavailableError('Cannot identify the existing storage mode while Docker is unavailable.')
            selection = self.discover(ready, container)
        if not selection:
            if docker_unavailable and not ready and (self.root / '.setup_done').exists():
                raise DockerUnavailableError('Waiting for Docker to inspect the existing Elasticsearch installation.')
            if ready or not (self.root / '.setup_done').exists():
                return
            raise RuntimeError('No managed Elasticsearch installation found.')
        if selection.get('mode') not in {'native', 'docker'}:
            raise RuntimeError('Invalid saved Elasticsearch storage mode.')
        try:
            self.migrate(selection, container)
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            print(f'Elasticsearch migration will be retried: {error}', file=sys.stderr)
            if not ready and selection['mode'] == 'docker':
                raise
        if ready:
            return
        if selection['mode'] == 'native':
            self.start_native(selection['home'])
        else:
            if container['State']['Running']:
                return  # Already starting; do not claim ownership.
            run(['docker', 'start', container['Id']])
            started = json.loads(run(['docker', 'inspect', container['Id']]))[0]
            self.record_owner(mode='docker', id=started['Id'], started_at=started['State']['StartedAt'])

    def stop(self):
        owner = read_json(self.owner_file)
        if not owner or not self.session or owner.get('session') != self.session:
            return
        if owner['mode'] == 'docker':
            current = self.docker_container()
            if not current or current['Id'] != owner['id'] or current['State']['StartedAt'] != owner['started_at']:
                return
            run(['docker', 'stop', '--time', '30', owner['id']], timeout=40)
        else:
            pid = int(owner['pid'])
            try:
                created, command = self.process_identity(pid)
            except (OSError, subprocess.SubprocessError, TypeError):
                return
            if created != owner['created'] or owner['home'] not in command:
                return
            if os.name == 'nt':
                stop_windows_console(pid)
            else:
                os.kill(pid, signal.SIGTERM)
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    current_created, _ = self.process_identity(pid)
                except (OSError, subprocess.SubprocessError, TypeError, json.JSONDecodeError):
                    break
                if current_created != created:
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError('Elasticsearch is still shutting down; it was not force-killed.')
        self.owner_file.unlink(missing_ok=True)


if __name__ == '__main__':
    lifecycle = ElasticsearchLifecycle(os.environ['VYACT_INSTALL_DIR'], os.environ.get('ES_PORT', '9251'))
    try:
        getattr(lifecycle, sys.argv[1])()
    except Exception as error:
        print(f'Elasticsearch lifecycle: {error}', file=sys.stderr)
        sys.exit(2 if isinstance(error, DockerUnavailableError) else 1)
