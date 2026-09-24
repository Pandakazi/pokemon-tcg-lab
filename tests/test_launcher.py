import importlib.util
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def launcher(tmp_path, monkeypatch):
    module = load_script("launcher")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    (tmp_path / "pyproject.toml").write_text("example requirements")
    (tmp_path / ".env.example").write_text("TCG_PORT=8000")
    return module


def test_first_install_no_pytest_and_preserves_settings(launcher, monkeypatch):
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        if "venv" in command:
            target = launcher.ROOT / ".venv"
            python = target / ("Scripts/python.exe" if launcher.os.name == "nt" else "bin/python")
            python.parent.mkdir(parents=True)
            python.touch()
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(launcher.subprocess, "run", run)
    launcher.prepare_environment()
    assert (launcher.ROOT / ".env").read_text() == "TCG_PORT=8000"
    assert any("venv" in c for c in calls)
    assert any("install" in c for c in calls)
    assert not any(arg in ("pytest", ".[dev]") or "import pytest" in arg for c in calls for arg in c)
    (launcher.ROOT / ".env").write_text("TCG_PORT=8123")
    calls.clear()
    launcher.prepare_environment()
    assert not any("install" in c for c in calls)
    assert (launcher.ROOT / ".env").read_text() == "TCG_PORT=8123"
    calls.clear()
    launcher.prepare_environment(repair=True)
    assert any("--force-reinstall" in c for c in calls)


def test_failed_install_does_not_mark_success(launcher, monkeypatch):
    target = launcher.ROOT / ".venv" / ("Scripts/python.exe" if launcher.os.name == "nt" else "bin/python")
    target.parent.mkdir(parents=True)
    target.touch()
    monkeypatch.setattr(launcher.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1 if "install" in cmd else 0))
    with pytest.raises(RuntimeError, match="Setup could not finish"):
        launcher.prepare_environment()
    assert not (launcher.ROOT / ".venv/.tcg-install-state").exists()


def test_missing_runtime_component_is_repaired(launcher, monkeypatch):
    target = launcher.ROOT / ".venv" / ("Scripts/python.exe" if launcher.os.name == "nt" else "bin/python")
    target.parent.mkdir(parents=True)
    target.touch()
    stamp = launcher.ROOT / ".venv/.tcg-install-state"
    stamp.write_text(launcher.hashlib.sha256((launcher.ROOT / "pyproject.toml").read_bytes()).hexdigest())
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        # First import fails; reinstall restores it.
        return subprocess.CompletedProcess(command, 1 if len(calls) == 1 else 0)
    monkeypatch.setattr(launcher.subprocess, "run", run)
    launcher.prepare_environment()
    assert any("--force-reinstall" in c for c in calls)


def test_occupied_port_falls_forward(launcher, monkeypatch, capsys):
    monkeypatch.setattr(launcher, "available", lambda port: port == 8002)
    assert launcher.choose_port(8000) == 8002
    assert "Other programs were left running" in capsys.readouterr().out
    monkeypatch.setattr(launcher, "available", lambda port: False)
    with pytest.raises(RuntimeError, match="No free address"):
        launcher.choose_port(65535)


def test_existing_lab_is_reported_without_starting(launcher, monkeypatch, capsys):
    monkeypatch.setattr(launcher, "health", lambda port: {"app": "pokemon-tcg-lab"})
    def no_process(*args, **kwargs):
        pytest.fail("Must not start another process")
    monkeypatch.setattr(launcher.subprocess, "Popen", no_process)
    assert launcher.serve(8000) == 0
    assert "already running" in capsys.readouterr().out


@pytest.mark.parametrize("payload", ["not-json", "[]", '{"port":true}', '{"port":22}', '{"port":"8000"}'])
def test_bad_status_file(launcher, payload):
    (launcher.ROOT / ".local-server.json").write_text(payload)
    assert launcher.read_last_port() is None


def test_distribution_allowlist(tmp_path):
    module = load_script("build_distribution")
    root = tmp_path / "source"
    root.mkdir()
    for name in module.TOP_FILES:
        (root / name).write_text("example\n")
    for name in [".env", "data/private.sqlite3", ".venv/bin/python", "src/tcg_lab/__pycache__/x.pyc", "debug.log", "build/secrets.json", "web/node_modules/private.js", "web/dist/app.js", "web/.env", "web/test-results/private.json"]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("private")
    output = tmp_path / "release.zip"
    module.build(root, output)
    with ZipFile(output) as archive:
        assert len(archive.namelist()) == len(module.TOP_FILES)
        assert all(name.startswith("pokemon-tcg-lab/") for name in archive.namelist())
        assert b"\r\n" in archive.read("pokemon-tcg-lab/Run-Local.ps1")
        assert b"\r" not in archive.read("pokemon-tcg-lab/Run-Local.command")
        assert (archive.getinfo("pokemon-tcg-lab/Run-Local.command").external_attr >> 16) & 0o111
