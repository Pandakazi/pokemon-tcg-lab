"""Shared beginner launcher. Bootstrap uses only Python's standard library."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
APP_ID = "pokemon-tcg-lab"


def say(message):
    print(message, flush=True)


def run_step(command, explanation):
    say(explanation)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        raise RuntimeError("Setup could not finish. Check your internet connection and the message above, then run the launcher again. For a repair, use -Repair on Windows or --repair on Mac. No deck data was removed.")


def prepare_environment(repair=False):
    target = ROOT / ".venv"
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        run_step([sys.executable, "-m", "venv", str(target)], "First-time setup: preparing Pokemon TCG Lab's private Python environment...")
    stamp = target / ".tcg-install-state"
    expected = hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest()
    installed = stamp.exists() and stamp.read_text() == expected
    broken = False
    if installed and not repair:
        for args in (["-c", "import tcg_lab.server"], ["-m", "pip", "check"]):
            result = subprocess.run([str(python), *args], cwd=ROOT, capture_output=True)
            if result.returncode:
                broken = True
                break
    if repair or broken or not installed:
        pip = subprocess.run([str(python), "-m", "pip", "--version"], capture_output=True)
        if pip.returncode:
            run_step([str(python), "-m", "ensurepip", "--upgrade"], "Repairing the installer...")
        command = [str(python), "-m", "pip", "--disable-pip-version-check", "install", "--upgrade"]
        if repair or broken:
            command.append("--force-reinstall")
        command += ["-e", str(ROOT)]
        run_step(command, "Installing Pokemon TCG Lab and required components. First setup needs internet and may take several minutes...")
        run_step([str(python), "-m", "pip", "check"], "Checking the installation...")
        run_step([str(python), "-c", "import tcg_lab.server"], "Checking that Pokemon TCG Lab can start...")
        stamp.write_text(expected)
    if not (ROOT / ".env").exists():
        shutil.copyfile(ROOT / ".env.example", ROOT / ".env")
    return python


def health(port):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port}/health", timeout=0.5) as response:
            data = json.loads(response.read(8192))
            return data if isinstance(data, dict) and data.get("app") == APP_ID else None
    except (OSError, ValueError):
        return None


def available(port):
    try:
        with socket.socket() as sock:
            if os.name == "nt":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def choose_port(preferred):
    for port in range(preferred, min(preferred + 20, 65536)):
        if available(port):
            if port != preferred:
                say(f"Port {preferred} is busy. Using {port} instead. Other programs were left running.")
            return port
    raise RuntimeError(f"No free address was found starting at port {preferred}. Try -Port 8100 on Windows or --port 8100 on Mac.")


def endpoint_message(port, already=False):
    say("Pokemon TCG Lab is already running." if already else "Pokemon TCG Lab is ready!")
    say(f"Local MCP endpoint: http://127.0.0.1:{port}/mcp")
    say(f"Browser check:      http://127.0.0.1:{port}/health")
    if already:
        say("Keep its original window open. That instance may belong to another extracted folder; use a different -Port/--port to run this copy separately.")
    else:
        say("DO NOT CLOSE THIS WINDOW WHILE USING POKEMON TCG LAB. Press Ctrl+C to stop.")


def read_last_port():
    try:
        value = json.loads((ROOT / ".local-server.json").read_text())["port"]
        return value if type(value) is int and 1024 <= value <= 65535 else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def serve(preferred):
    if health(preferred):
        endpoint_message(preferred, already=True)
        return 0
    port = choose_port(preferred)
    startup_id = uuid4().hex
    env = {**os.environ, "TCG_PORT": str(port), "PYTHONUNBUFFERED": "1", "TCG_STARTUP_ID": startup_id}
    say("Starting Pokemon TCG Lab...")
    process = subprocess.Popen([sys.executable, "-m", "tcg_lab.server"], cwd=ROOT, env=env)
    try:
        for _ in range(150):
            if process.poll() is not None:
                raise RuntimeError("The server stopped before it was ready. Read the message above. If another program just took the address, rerun the launcher to find a free port.")
            result = health(port)
            if result and result.get("startup_id") == startup_id:
                (ROOT / ".local-server.json").write_text(json.dumps({"port": port}))
                endpoint_message(port)
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("The server did not become ready. Check the messages above and try -Repair/--repair.")
        code = process.wait()
        if code:
            raise RuntimeError("The server stopped with an error. See the message above and Troubleshooting in README.md.")
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main():
    parser = argparse.ArgumentParser(description="Set up, start, repair or check Pokemon TCG Lab.")
    parser.add_argument("--port", type=int)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--ready", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not (3, 11) <= sys.version_info[:2] < (4, 0):
        raise RuntimeError("Python 3.11 or newer is required. Download Python 3 from https://www.python.org/downloads/.")
    os.chdir(ROOT)
    if not args.ready:
        python = prepare_environment(args.repair)
        return subprocess.call([str(python), str(Path(__file__).resolve()), *sys.argv[1:], "--ready"], cwd=ROOT)
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    configured = args.port if args.port is not None else int(os.getenv("TCG_PORT", "8000"))
    if not 1024 <= configured <= 65535:
        raise RuntimeError("Choose a port between 1024 and 65535 (normally 8000).")
    last = read_last_port() if args.port is None else None
    selected = last if last and health(last) else configured
    if args.check:
        return subprocess.call([sys.executable, str(ROOT / "scripts/check_server.py"), "--port", str(selected)], cwd=ROOT)
    return serve(selected)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        say("\nPokemon TCG Lab stopped. Saved decks are still in your data folder.")
        sys.exit(0)
    except (OSError, RuntimeError, ValueError) as error:
        say(f"\nCould not start Pokemon TCG Lab: {error}")
        say("Your saved decks have not been deleted. See Troubleshooting in README.md.")
        sys.exit(1)
