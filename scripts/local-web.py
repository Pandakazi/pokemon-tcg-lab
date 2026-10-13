"""POSIX web launcher: existing app, local databases, no provider requests."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/local-web-posix'
RECORD = STATE / 'processes.json'
PYTHON = ROOT / '.venv/bin/python'
API_PORT, WEB_PORT = 8001, 5173


def say(message):
    print(message, flush=True)


@contextmanager
def launch_lock():
    import fcntl
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'launch.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another setup/start/stop is in progress. Wait, then try again.') from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def run(command, message, *, env=None):
    say(message)
    result = subprocess.run([str(x) for x in command], cwd=ROOT, env=env)
    if result.returncode:
        raise RuntimeError('This step failed. Check the message above and rerun setup. Your collection and decks are preserved.')


def tools():
    node, npm = shutil.which('node'), shutil.which('npm')
    if not node or not npm:
        raise RuntimeError('Node.js is required. Install Node.js LTS from nodejs.org, reopen Terminal, then rerun setup.')
    result = subprocess.run([node, '-e', "const [a,b]=process.versions.node.split('.').map(Number);process.exit((a===22&&b>=12)||a>=24?0:1)"], timeout=10)
    if result.returncode:
        raise RuntimeError('Install Node.js LTS 22.12+ or 24+, reopen Terminal, then rerun setup.')
    return node, npm


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup(args):
    _, npm = tools()
    if not PYTHON.exists():
        run([sys.executable, '-m', 'venv', ROOT / '.venv'], 'Creating the private Python environment...')
    stamp = ROOT / '.venv/pokelab-posix-install.sha256'
    expected = digest(ROOT / 'pyproject.toml')
    check = subprocess.run([str(PYTHON), '-c', 'import fastapi,uvicorn,httpx,mcp,dotenv,pokelab.api'], cwd=ROOT, capture_output=True)
    if check.returncode or not stamp.exists() or stamp.read_text().strip() != expected:
        command = [PYTHON, '-m', 'pip', '--disable-pip-version-check', 'install', '-e', '.[web]']
        if args.offline:
            command += ['--no-index', '--no-build-isolation']
        run(command, 'Installing backend dependencies (first setup needs internet)...')
        stamp.write_text(expected)
    run([PYTHON, '-m', 'pip', 'check'], 'Checking backend dependencies...')
    web_stamp = ROOT / 'web/node_modules/.pokelab-posix-install.sha256'
    expected = digest(ROOT / 'web/package-lock.json')
    if not (ROOT / 'web/node_modules/vite/bin/vite.js').exists() or not web_stamp.exists() or web_stamp.read_text().strip() != expected:
        command = [npm, '--prefix', 'web', 'ci', '--no-audit', '--no-fund']
        if args.offline:
            command += ['--offline']
        run(command, 'Installing frontend dependencies...')
        web_stamp.write_text(expected)
    command = [PYTHON, ROOT / 'scripts/bootstrap-web.py']
    if args.offline:
        command += ['--offline']
    for option in ('cards_database', 'competitive_database'):
        value = getattr(args, option)
        if value:
            command += ['--' + option.replace('_', '-'), str(Path(value).expanduser().resolve())]
    run(command, 'Preparing local databases and indexes...')
    say('Setup complete! Run bash start.sh to open PokeLab.')
    say('Settings > Agent Settings > Gemini API key > Test & Apply. No .env editing is needed.')


def fingerprint(pid):
    """BSD/macOS and Linux ps: timestamp plus full command, never PID alone."""
    if sys.platform == 'linux':
        # Kernel start ticks do not move when WSL adjusts its wall clock.
        try:
            proc = Path('/proc') / str(pid)
            fields = (proc/'stat').read_text().rsplit(')',1)[1].split()
            if fields[0] == 'Z':
                return None
            command = (proc/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()
            return fields[19] + ' ' + command if command else None
        except FileNotFoundError:
            return None
    result = subprocess.run(['ps', '-ww', '-p', str(pid), '-o', 'stat=', '-o', 'lstart=', '-o', 'args='], capture_output=True, text=True, timeout=5)
    line = result.stdout.strip()
    if result.returncode or not line or line.split()[0].startswith('Z'):
        return None
    # Process state changes (sleeping/running) are not part of its identity.
    return line.split(None, 1)[1]


def owned_tasks():
    if not RECORD.exists():
        return []
    record = json.loads(RECORD.read_text())
    if record.get('root') != str(ROOT):
        raise RuntimeError('The launch record belongs to another folder. No process was stopped.')
    tasks = []
    for task in record['tasks']:
        actual = fingerprint(task['pid'])
        if actual is None:
            continue
        if actual != task['identity'] or str(ROOT) not in actual or os.getpgid(task['pid']) != task['pid']:
            raise RuntimeError(f"Recorded process {task['pid']} no longer belongs to this launch. No process was stopped.")
        tasks.append(task)
    return tasks


def terminate(tasks):
    # Caller validates all recorded identities before any signal is sent.
    for task in tasks:
        try:
            os.killpg(task['pid'], signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 10
    while any(fingerprint(t['pid']) is not None for t in tasks):
        if time.monotonic() >= deadline:
            raise RuntimeError('The server did not stop within 10 seconds. Check the logs before starting again.')
        time.sleep(.1)


def stop():
    terminate(owned_tasks())
    RECORD.unlink(missing_ok=True)


def available(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def healthy():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        for port in (API_PORT, WEB_PORT):
            with opener.open(f'http://127.0.0.1:{port}/api/v1/status', timeout=2) as response:
                status = json.load(response)
                if status.get('source') != 'TCGdex SQLite' or not status.get('ready') or not status.get('cards'):
                    return False
        with opener.open(f'http://127.0.0.1:{WEB_PORT}/', timeout=2) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def start(args):
    node, _ = tools()
    vite = ROOT / 'web/node_modules/vite/bin/vite.js'
    if not PYTHON.exists() or not vite.exists() or not (ROOT / 'data/cards.sqlite3').exists():
        raise RuntimeError('Setup is required first. Run bash setup.sh, then bash start.sh.')
    tasks = owned_tasks()
    if len(tasks) == 2 and healthy():
        say('PokeLab is already running.')
    else:
        stop()
        for port in (API_PORT, WEB_PORT):
            if not available(port):
                raise RuntimeError(f'Port {port} is already in use. Close that program, then rerun start. No unrelated process was stopped.')
        run([PYTHON, ROOT / 'scripts/bootstrap-web.py', '--offline'], 'Preparing local indexes offline...')
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'),
                   TCG_CARDS_DB_PATH=str(ROOT / 'data/cards.sqlite3'),
                   POKELAB_USER_DB_PATH=str(ROOT / 'data/user-state.sqlite3'),
                   POKELAB_DECK_DB_PATH=str(ROOT / 'data/deck-workspace.sqlite3'),
                   POKELAB_COMPETITIVE_DB_PATH=str(ROOT / 'data/competitive.sqlite3'),
                   POKELAB_API_TARGET=f'http://127.0.0.1:{API_PORT}')
        revision = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=5) if shutil.which('git') else None
        env['POKELAB_BUILD_REVISION'] = revision.stdout.strip() if revision and not revision.returncode else 'local-preview'
        processes = []
        try:
            commands = [("api", [str(PYTHON), '-m', 'uvicorn', 'pokelab.api:app', '--app-dir', str(ROOT / 'src'), '--host', '127.0.0.1', '--port', str(API_PORT)], ROOT),
                        ("web", [node, str(vite), '--host', '127.0.0.1', '--port', str(WEB_PORT), '--strictPort'], ROOT / 'web')]
            for label, command, cwd in commands:
                with (STATE / f'{label}.out.log').open('w') as out, (STATE / f'{label}.err.log').open('w') as err:
                    processes.append(subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True))
            tasks = [{'pid': p.pid, 'identity': fingerprint(p.pid)} for p in processes]
            if any(not t['identity'] for t in tasks):
                raise RuntimeError('A server exited during launch. Check the logs.')
            temporary = RECORD.with_suffix('.tmp')
            temporary.write_text(json.dumps({'root': str(ROOT), 'tasks': tasks}))
            temporary.chmod(0o600)
            temporary.replace(RECORD)
            deadline = time.monotonic() + 60
            while not healthy():
                if any(p.poll() is not None for p in processes) or time.monotonic() >= deadline:
                    raise RuntimeError(f'Servers did not become ready within 60 seconds. See logs in {STATE}.')
                time.sleep(.2)
        except BaseException:
            # These are newly created session groups, not arbitrary saved PIDs.
            terminate([{'pid': p.pid} for p in processes if p.poll() is None])
            RECORD.unlink(missing_ok=True)
            raise
    url = f'http://127.0.0.1:{WEB_PORT}/'
    say(f'PokeLab ready: {url} (API: http://127.0.0.1:{API_PORT})')
    say('Stop: bash stop.sh    Restart: bash stop.sh, then bash start.sh')
    if not args.no_browser:
        if sys.platform == 'darwin':
            result = subprocess.run(['open', url], timeout=10)
            if result.returncode:
                say(f'Open {url} in your browser.')
        else:
            say(f'Open {url} in your browser.')


def main():
    parser = argparse.ArgumentParser(description='Set up, start, or stop the local macOS/POSIX web app.')
    sub = parser.add_subparsers(dest='action', required=True)
    installer = sub.add_parser('setup')
    installer.add_argument('--offline', action='store_true')
    installer.add_argument('--cards-database')
    installer.add_argument('--competitive-database')
    starter = sub.add_parser('start')
    starter.add_argument('--no-browser', action='store_true')
    sub.add_parser('stop')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        raise RuntimeError('Python 3.11+ is required. Install Python from python.org.')
    if os.name != 'posix':
        raise RuntimeError('Use setup.ps1/start.ps1/stop.ps1 on Windows.')
    os.chdir(ROOT)
    with launch_lock():
        if args.action == 'setup':
            setup(args)
        elif args.action == 'start':
            start(args)
        else:
            stop()
            say('PokeLab stopped. Your collection and decks are preserved.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        say(f'PokeLab: {error}')
        sys.exit(1)
    except KeyboardInterrupt:
        say('Interrupted. Rerun the command when ready; saved data is preserved.')
        sys.exit(1)
