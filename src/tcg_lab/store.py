"""Single-owner SQLite storage; append-only versions, transactional writes."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .models import Deck


class DeckStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS deck_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_key TEXT NOT NULL, version TEXT NOT NULL,
                payload TEXT NOT NULL, validation TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(name_key, version))""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save(self, deck: Deck, validation: dict) -> dict:
        created_at = datetime.now(timezone.utc).isoformat()
        try:
            with self.connect() as db:
                db.execute("INSERT INTO deck_versions(name_key,version,payload,validation,created_at) VALUES(?,?,?,?,?)",
                           (deck.name.casefold(), deck.version, deck.model_dump_json(), json.dumps(validation), created_at))
        except sqlite3.IntegrityError as exc:
            raise ValueError("That deck version already exists. Choose a new version; existing versions are never overwritten.") from exc
        return self.get(deck.name, deck.version)

    def get(self, name: str, version: str | None = None) -> dict:
        with self.connect() as db:
            sql = "SELECT payload,validation,created_at FROM deck_versions WHERE name_key=?"
            params: list = [name.strip().casefold()]
            if version is not None:
                sql += " AND version=?"
                params.append(version.strip())
            row = db.execute(sql + " ORDER BY id DESC LIMIT 1", params).fetchone()
            if row is None:
                raise ValueError("Saved deck/version not found.")
            versions = [r[0] for r in db.execute("SELECT version FROM deck_versions WHERE name_key=? ORDER BY id", (params[0],))]
        return {"deck": json.loads(row[0]), "validation_at_save": json.loads(row[1]),
                "created_at": row[2], "available_versions": versions}
