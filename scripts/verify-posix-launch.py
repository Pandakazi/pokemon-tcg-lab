"""Offline smoke test in a disposable checkout only; no provider requests."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/local-web-posix/processes.json'


def command(*args, success=True):
    result = subprocess.run(['bash', *args], cwd=ROOT, timeout=240)
    assert (result.returncode == 0) == success, (args, result.returncode)


def fixture():
    path = ROOT / '.cache/mac-smoke-input/cards.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path
    card = dict(id='svtest-1', name='Probe Pokemon', category='Pokemon', localId='1',
                set=dict(id='svtest', name='Offline fixture'), regulationMark='H',
                hp=70, stage='Basic', types=['Colorless'], attacks=[], legal=dict(standard=True, expanded=True))
    with sqlite3.connect(path) as db:
        db.execute('''CREATE TABLE cards (id TEXT PRIMARY KEY,name TEXT,name_fold TEXT,set_id TEXT,
          number TEXT,category TEXT,trainer_type TEXT,regulation TEXT,game TEXT,standard INTEGER,
          expanded INTEGER,text_fold TEXT,raw TEXT,fetched_at TEXT,checked_at TEXT,etag TEXT,modified TEXT)''')
        db.execute('INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   ('svtest-1','Probe Pokemon','probe pokemon','svtest','1','Pokemon',None,'H','tcg',1,1,'',json.dumps(card),'2026-10-11T00:00:00+00:00','2026-10-11T00:00:00+00:00',None,None))
    return path


def request(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=5) as response:
        return json.load(response)


def snapshots():
    return {name: hashlib.sha256((ROOT / 'data' / name).read_bytes()).hexdigest()
            for name in ('user-state.sqlite3','deck-workspace.sqlite3')}


def main():
    if os.getenv('POKELAB_EXPECT_MAC_ARM64') == '1':
        assert sys.platform == 'darwin' and os.uname().machine == 'arm64', 'Expected Apple Silicon macOS runner'
    assert not (ROOT / 'data').exists(), 'Run smoke verification only in a fresh disposable clone.'
    for name in ('setup.sh','start.sh','stop.sh'):
        subprocess.run(['bash','-n',str(ROOT/name)],check=True)
    source = fixture()
    command('setup.sh','--cards-database',str(source))
    with sqlite3.connect(ROOT/'data/user-state.sqlite3') as db:
        db.execute('INSERT INTO collection VALUES (?,?,?)', ('svtest-1','normal',3))
    before = snapshots()
    command('setup.sh','--offline')
    assert snapshots() == before, 'Setup changed saved collection/decks'
    try:
        command('start.sh','--no-browser')
        assert request('http://127.0.0.1:8001/api/v1/status')['ready']
        assert request('http://127.0.0.1:5173/api/v1/status')['ready']
        settings = request('http://127.0.0.1:8001/api/v1/settings/agent')
        assert not settings['connected'] and settings['storage'] in ('external','session')
        before_record = STATE.read_bytes()
        command('start.sh','--no-browser')
        assert STATE.read_bytes() == before_record, 'Repeated start spawned new processes'
        corrupted = json.loads(before_record)
        corrupted['tasks'][0]['identity'] = 'wrong process identity'
        STATE.write_text(json.dumps(corrupted))
        try:
            command('stop.sh',success=False)
            assert request('http://127.0.0.1:8001/api/v1/status')['ready'], 'Invalid record stopped a server'
        finally:
            STATE.write_bytes(before_record)
        tasks = json.loads(before_record)['tasks']
        os.kill(tasks[1]['pid'], 15)
        time.sleep(.5)
        command('start.sh','--no-browser')
        assert request('http://127.0.0.1:5173/api/v1/status')['ready']
    finally:
        command('stop.sh')
    command('stop.sh')
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1',8001)); listener.listen()
        command('start.sh','--no-browser',success=False)
        assert listener.getsockname()[1] == 8001
    command('start.sh','--no-browser')
    command('stop.sh')
    assert snapshots() == before, 'Launch/stop changed saved collection/decks'
    for port in (8001,5173):
        with socket.socket() as probe:
            assert probe.connect_ex(('127.0.0.1',port)) != 0, 'Stop left a server listening'
    spec = importlib.util.spec_from_file_location('local_web', ROOT/'scripts/local-web.py')
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    from unittest.mock import patch
    with patch.object(launcher.shutil,'which',return_value=None):
        try:
            launcher.tools()
            raise AssertionError('Missing Node was accepted')
        except RuntimeError as error:
            assert 'Install Node.js LTS' in str(error)
    print(f'PASS POSIX launcher smoke: {sys.platform}; {os.uname().machine}',flush=True)


if __name__ == '__main__':
    main()
