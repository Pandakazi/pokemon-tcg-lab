"""Build Windows x64 PokeLab.exe, optionally embedding a complete text-only cache."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=ROOT / "data/cards.sqlite3")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if sys.platform != "win32" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise SystemExit("Build this Windows executable on Windows x64.")
    with closing(sqlite3.connect(f"file:{args.seed.as_posix()}?mode=ro", uri=True)) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not tables <= {"cards", "sets", "metadata"}:
            raise SystemExit("Seed contains non-card tables. Use the original TCGdex-only cards.sqlite3, never a player profile.")
        row = db.execute("SELECT value FROM metadata WHERE key='last_sync'").fetchone()
        if not row or json.loads(row[0]).get("status") != "complete":
            raise SystemExit("Finish the card sync before building a seeded executable.")
    args.output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
               "--name", "PokeLab", "--paths", str(ROOT / "src"),
               "--distpath", str(args.output), "--workpath", str(ROOT / "build/desktop"),
               "--specpath", str(ROOT / "build"), "--add-data", f"{args.seed};seed",
               "--exclude-module", "mcp", "--exclude-module", "pytest", str(ROOT / "scripts/pokelab_entry.py")]
    subprocess.run(command, cwd=ROOT, check=True)
    print(f"Built {args.output / 'PokeLab.exe'}")


if __name__ == "__main__":
    main()
