"""Local canonical card records. Reads never contact the network."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .cards import BASE_URL, CardLookupError, check_id, check_search, public_card, summary


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def parse_card(card, expected_id=None):
    """Keep source JSON intact; reject incomplete/corrupt replacements."""
    if not isinstance(card, dict):
        raise CardLookupError("TCGdex returned a non-object card.")
    check_id(card.get("id", ""))
    if expected_id is not None and card["id"] != expected_id:
        raise CardLookupError("TCGdex returned a mismatched printing ID.")
    if (not isinstance(card.get("name"), str) or not card["name"].strip()
            or card.get("category") not in ("Pokemon", "Trainer", "Energy")
            or not isinstance(card.get("set"), dict) or not isinstance(card["set"].get("id"), str)
            or not card["set"]["id"] or type(card.get("localId")) not in (str, int)):
        raise CardLookupError("TCGdex returned an incomplete card record.")
    for field in ("attacks", "abilities", "types", "weaknesses", "resistances"):
        if field in card and not isinstance(card[field], list):
            raise CardLookupError(f"TCGdex returned invalid {field}.")
    legal = card.get("legal", {})
    if not isinstance(legal, dict) or any(type(v) is not bool for v in legal.values()):
        raise CardLookupError("TCGdex returned invalid legality flags.")
    return card


class SQLiteCards:
    def __init__(self, path="data/cards.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise CardLookupError("Unsupported card database version; upgrade Pokemon TCG Lab.")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, name_fold TEXT NOT NULL,
                    set_id TEXT NOT NULL, number TEXT NOT NULL, category TEXT NOT NULL,
                    trainer_type TEXT, regulation TEXT, game TEXT NOT NULL,
                    standard INTEGER, expanded INTEGER, text_fold TEXT NOT NULL,
                    raw TEXT NOT NULL, fetched_at TEXT NOT NULL, checked_at TEXT NOT NULL,
                    etag TEXT, modified TEXT);
                CREATE INDEX IF NOT EXISTS cards_name ON cards(name_fold);
                CREATE INDEX IF NOT EXISTS cards_set_number ON cards(set_id, number);
                CREATE INDEX IF NOT EXISTS cards_format ON cards(game, standard, expanded);
                CREATE INDEX IF NOT EXISTS cards_subtype ON cards(trainer_type, regulation);
                CREATE TABLE IF NOT EXISTS sets (id TEXT PRIMARY KEY, raw TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                PRAGMA user_version=1;
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def metadata(self, key, value=None):
        with closing(self.connect()) as db, db:
            if value is not None:
                db.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", (key, json.dumps(value)))
                return value
            row = db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None

    def status(self):
        with closing(self.connect()) as db:
            count = db.execute("SELECT count(*) FROM cards").fetchone()[0]
        return {"cards": count, "last_sync": self.metadata("last_sync")}

    def put_set(self, record):
        if not isinstance(record, dict) or not record.get("id") or not isinstance(record.get("serie"), dict):
            raise CardLookupError("TCGdex returned incomplete set metadata.")
        with closing(self.connect()) as db, db:
            db.execute("INSERT OR REPLACE INTO sets VALUES (?, ?)", (record["id"], json.dumps(record)))
            serie = record["serie"].get("id")
            game = "pocket" if serie == "tcgp" else "tcg" if serie else "unknown"
            db.execute("UPDATE cards SET game=? WHERE set_id=?", (game, record["id"]))

    def put(self, card, *, fetched_at=None, etag=None, modified=None):
        card = parse_card(card)
        stamp = fetched_at or utcnow()
        set_id = card["set"]["id"]
        with closing(self.connect()) as db, db:
            set_row = db.execute("SELECT raw FROM sets WHERE id=?", (set_id,)).fetchone()
            set_data = json.loads(set_row[0]) if set_row else card["set"]
            serie = set_data.get("serie", {}).get("id")
            game = "pocket" if serie == "tcgp" else "tcg" if serie else "unknown"
            legal = card.get("legal", {})
            text_fields = {k: card[k] for k in ("name", "effect", "description", "abilities", "attacks", "rules", "suffix", "stage", "trainerType", "energyType") if k in card}
            values = (card["id"], card["name"], card["name"].casefold(), set_id,
                      str(card["localId"]), card["category"], card.get("trainerType"),
                      card.get("regulationMark"), game, legal.get("standard"), legal.get("expanded"),
                      json.dumps(text_fields, ensure_ascii=False).casefold(),
                      json.dumps(card, ensure_ascii=False, separators=(",", ":")), stamp, stamp, etag, modified)
            db.execute("INSERT OR REPLACE INTO cards VALUES (" + ",".join("?" for _ in values) + ")", values)

    def cached(self):
        with closing(self.connect()) as db:
            return {r["id"]: dict(r) for r in db.execute("SELECT id,checked_at,etag,modified FROM cards")}

    def touch(self, card_id):
        with closing(self.connect()) as db, db:
            db.execute("UPDATE cards SET checked_at=? WHERE id=?", (utcnow(), card_id))

    def _ready(self, db):
        if not db.execute("SELECT 1 FROM cards LIMIT 1").fetchone():
            raise CardLookupError("Card database is empty. Run python -m tcg_lab.sync_cards using the project's .venv Python, then retry. See README: Initialize or update cards.")

    def get(self, card_id, include_image=False):
        check_id(card_id)
        with closing(self.connect()) as db:
            self._ready(db)
            row = db.execute("SELECT cards.raw,fetched_at,checked_at,game,sets.raw AS set_raw FROM cards LEFT JOIN sets ON sets.id=cards.set_id WHERE cards.id=?", (card_id,)).fetchone()
        if not row:
            raise CardLookupError(f"Printing {card_id} is not in the local database. Search by name first and use an exact returned ID; run sync if the database is incomplete.")
        card = json.loads(row["raw"])
        if row["set_raw"]:
            set_metadata = json.loads(row["set_raw"])
            code = set_metadata.get("tcgOnline") or set_metadata.get("abbreviation", {}).get("official")
            if code:
                card["set"]["code"] = code
        return {"card": public_card(card, include_image), "source": "TCGdex SQLite",
                "fetched_at": row["fetched_at"], "checked_at": row["checked_at"], "live": False,
                "game": row["game"]}

    def search(self, query="", page=1, page_size=20, include_image=False, **filters):
        filters = {k: v for k, v in filters.items() if v is not None}
        check_search(query, page, page_size, allow_empty=bool(filters))
        clauses, params = [], []
        if query.strip():
            clauses.append("(instr(name_fold, ?) > 0 OR id = ?)")
            params.extend((query.strip().casefold(), query.strip()))
        columns = {"set_id": "set_id", "collector_number": "number", "category": "category",
                   "trainer_type": "trainer_type", "regulation_mark": "regulation", "game": "game"}
        for key, column in columns.items():
            if key in filters:
                if key == "set_id":
                    clauses.append("(set_id = ? COLLATE NOCASE OR set_id IN (SELECT id FROM sets WHERE json_extract(raw, '$.tcgOnline') = ? COLLATE NOCASE OR json_extract(raw, '$.abbreviation.official') = ? COLLATE NOCASE))")
                    params.extend((filters[key], filters[key], filters[key]))
                    continue
                clauses.append(f"{column} = ? COLLATE NOCASE")
                params.append(filters[key])
        if "game" not in filters:
            clauses.append("game != 'pocket'")
        if "text" in filters:
            clauses.append("instr(text_fold, ?) > 0")
            params.append(filters["text"].casefold())
        if "pokemon_type" in filters:
            clauses.append("EXISTS (SELECT 1 FROM json_each(raw, '$.types') WHERE value = ? COLLATE NOCASE)")
            params.append(filters["pokemon_type"])
        # Multi-select families: one OR/IN clause each, joined by AND below.
        families = {"pokemon_types": "EXISTS (SELECT 1 FROM json_each(raw, '$.types') WHERE value IN ({marks}))",
                    "stages": "json_extract(raw,'$.stage') IN ({marks})",
                    "trainer_types": "trainer_type IN ({marks})",
                    "energy_types": "json_extract(raw,'$.energyType') IN ({marks})",
                    "regulation_marks": "regulation IN ({marks})"}
        for key, expression in families.items():
            selected = filters.get(key, ())
            if not isinstance(selected, (list, tuple)) or len(selected) > 26 or any(not isinstance(v, str) or len(v) > 30 for v in selected):
                raise ValueError("Invalid multi-select filter")
            if selected:
                clauses.append(expression.format(marks=",".join("?" for _ in selected)))
                params.extend(selected)
        if 'has_ability' in filters and type(filters['has_ability']) is not bool:
            raise ValueError('has_ability must be boolean')
        if filters.get('has_ability'):
            clauses.append("category='Pokemon' AND EXISTS (SELECT 1 FROM json_each(raw,'$.abilities') a WHERE json_extract(a.value,'$.type')='Ability')")
        if "format" in filters:
            fmt = filters["format"]
            if fmt not in ("standard", "expanded", "unlimited"):
                raise ValueError("format must be standard, expanded or unlimited")
            legality = filters.get("legality", "legal")
            if legality not in ("legal", "not_legal", "unknown"):
                raise ValueError("legality must be legal, not_legal or unknown")
            column = fmt if fmt != "unlimited" else "NULL"
            clauses.append(f"{column} IS NULL" if legality == "unknown" else f"{column} = ?")
            if legality != "unknown":
                params.append(int(legality == "legal"))
        elif "legality" in filters:
            raise ValueError("legality requires format")
        if set(filters) - (set(columns) | set(families) | {"text", "pokemon_type", "format", "legality", "has_ability"}):
            raise ValueError("Unsupported search filter")
        where = " AND ".join(clauses) or "1"
        with closing(self.connect()) as db:
            self._ready(db)
            total, rows = self._search_page(db, where, params, page, page_size)
        result = {"cards": [dict(summary(json.loads(r["raw"]), include_image), game=r["game"]) for r in rows],
                  "page": page, "page_size": page_size, "total": total,
                  "next_page": page + 1 if page * page_size < total else None, "scope": "local TCGdex database"}
        status = self.metadata("last_sync")
        if status:
            result["sync"] = {k: status[k] for k in ("status", "finished_at", "missing") if k in status}
        else:
            result["sync"] = {"status": "not_completed"}
        return result

    def _search_page(self, db, where, params, page, page_size):
        """Exact-printing pagination; presentation adapters may select representatives."""
        total = db.execute(f"SELECT count(*) FROM cards WHERE {where}", params).fetchone()[0]
        rows = db.execute(f"SELECT raw,game FROM cards WHERE {where} ORDER BY id LIMIT ? OFFSET ?",
                          [*params, page_size, (page - 1) * page_size]).fetchall()
        return total, rows
