"""Separate application assets from writable player data."""
import os
from pathlib import Path
import shutil
import sys


def prepare_data(directory: str | None = None) -> Path:
    root = Path(directory) if directory else Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PokeLab"
    root.mkdir(parents=True, exist_ok=True)
    database = root / "pokelab.sqlite3"
    if not database.exists():
        asset_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
        seed = asset_root / "seed" / "cards.sqlite3"
        if not seed.exists() and not getattr(sys, "frozen", False):
            seed = Path(__file__).resolve().parents[2] / "data" / "cards.sqlite3"
        if seed.exists():
            temporary = database.with_suffix(".copying")
            shutil.copyfile(seed, temporary)
            temporary.replace(database)
    return database
