"""Local card browser, conservative functional identities, and collection writes.

This module has no Qt, MCP, or AI dependency. All collection mutations originate
from explicit player actions; the agent is given a separate read-only facade.
"""
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import unicodedata

from tcg_lab.card_db import SQLiteCards
from tcg_lab.cards import summary

POKEMON_TYPES = ("Colorless", "Darkness", "Dragon", "Fairy", "Fighting", "Fire", "Grass", "Lightning", "Metal", "Psychic", "Water")


def normalized_name(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().replace("’", "'").strip()


def functional_signature(card: dict) -> str:
    """Conservatively group identical gameplay records, never names alone.

    Artwork, rarity, set, and regulation mark are printing properties. Missing
    rules text must not accidentally merge unrelated same-name cards. Wording
    changes remain separate until a curated equivalence rule is introduced.
    """
    fields = ("name", "category", "hp", "types", "stage", "suffix", "evolveFrom",
              "abilities", "attacks", "effect", "rules", "weaknesses", "resistances",
              "retreat", "trainerType", "energyType")
    identity = {key: card[key] for key in fields if key in card}
    identity["name"] = normalized_name(card["name"])
    has_rules = any(card.get(key) for key in ("abilities", "attacks", "effect", "rules"))
    if not has_rules and not (card.get("category") == "Energy" and card.get("energyType") == "Normal"):
        identity["unresolved_printing"] = card["id"]
    return json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class CardQuery:
    """OR within a tuple-valued family; AND between families."""
    text: str = ""
    category: str | None = None
    ownership: str = "all"
    types: tuple[str, ...] = ()
    trainer_types: tuple[str, ...] = ()
    page: int = 1
    page_size: int = 40


class PokeLabEngine:
    def __init__(self, database: str | Path):
        self.cards = SQLiteCards(database)
        self.path = self.cards.path
        with closing(self.cards.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS functional_cards (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, signature TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS printing_identity (
                    printing_id TEXT PRIMARY KEY, functional_id TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS identity_function ON printing_identity(functional_id);
                CREATE TABLE IF NOT EXISTS collection (
                    printing_id TEXT NOT NULL, variant TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK(quantity >= 0 AND quantity <= 9999),
                    PRIMARY KEY(printing_id, variant));
                CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)

    def rebuild_identities(self) -> int:
        """Run after sync, in a worker. Preserve printing-specific ownership."""
        with closing(self.cards.connect()) as db, db:
            count = 0
            for row in db.execute("SELECT id,raw FROM cards").fetchall():
                card = json.loads(row["raw"])
                signature = functional_signature(card)
                identity = hashlib.sha256(signature.encode()).hexdigest()[:32]
                db.execute("INSERT OR IGNORE INTO functional_cards VALUES (?,?,?)", (identity, card["name"], signature))
                db.execute("INSERT OR REPLACE INTO printing_identity VALUES (?,?)", (row["id"], identity))
                count += 1
            db.execute("INSERT OR REPLACE INTO app_settings VALUES ('identity_version', '1')")
        return count

    def identity(self, printing_id: str) -> str:
        with closing(self.cards.connect()) as db:
            row = db.execute("SELECT functional_id FROM printing_identity WHERE printing_id=?", (printing_id,)).fetchone()
        if row is None:
            raise ValueError("Card identities need updating. Refresh card data first.")
        return row[0]

    def browse(self, query: CardQuery) -> dict:
        if query.category not in (None, "Pokemon", "Trainer", "Energy") or query.ownership not in ("all", "owned", "unowned"):
            raise ValueError("Invalid browser filter")
        if not set(query.types) <= set(POKEMON_TYPES) or not 1 <= query.page_size <= 100 or query.page < 1 or len(query.text) > 200:
            raise ValueError("Invalid query bounds or Pokemon types")
        clauses = ["c.standard=1", "c.game='tcg'"]
        values: list = []
        if query.text.strip():
            clauses.append("(instr(c.name_fold,?)>0 OR c.id=?)")
            values += [query.text.strip().casefold(), query.text.strip()]
        if query.category:
            clauses.append("c.category=?")
            values.append(query.category)
        if query.ownership != "all":
            clauses.append("COALESCE(o.quantity,0)>0" if query.ownership == "owned" else "COALESCE(o.quantity,0)=0")
        # Each filter family compiles one clause. Values never become SQL source.
        for selected, expression in ((query.types, "EXISTS (SELECT 1 FROM json_each(c.raw,'$.types') WHERE value IN ({marks}))"),
                                     (query.trainer_types, "c.trainer_type IN ({marks})")):
            if selected:
                clauses.append(expression.format(marks=",".join("?" for _ in selected)))
                values.extend(selected)
        from_sql = "FROM cards c LEFT JOIN (SELECT printing_id,SUM(quantity) quantity FROM collection GROUP BY printing_id) o ON o.printing_id=c.id"
        where = " AND ".join(clauses)
        with closing(self.cards.connect()) as db:
            total = db.execute(f"SELECT count(*) {from_sql} WHERE {where}", values).fetchone()[0]
            rows = db.execute(f"SELECT c.raw,COALESCE(o.quantity,0) owned {from_sql} WHERE {where} ORDER BY c.name_fold,c.id LIMIT ? OFFSET ?",
                              [*values, query.page_size, (query.page-1)*query.page_size]).fetchall()
        return {"total": total, "cards": [dict(summary(json.loads(row["raw"]), True), owned=row["owned"]) for row in rows]}

    def collection_quantity(self, printing_id: str, variant: str = "unspecified") -> int:
        with closing(self.cards.connect()) as db:
            row = db.execute("SELECT quantity FROM collection WHERE printing_id=? AND variant=?", (printing_id, variant)).fetchone()
        return row[0] if row else 0

    def set_quantity(self, printing_id: str, variant: str, quantity: int) -> int:
        if type(quantity) is not int or not 0 <= quantity <= 9999 or not variant or len(variant) > 100:
            raise ValueError("Quantity must be a whole number from 0 to 9999.")
        self.cards.get(printing_id)  # Reject nonexistent IDs, even through direct engine calls.
        with closing(self.cards.connect()) as db, db:
            db.execute("INSERT INTO collection VALUES (?,?,?) ON CONFLICT(printing_id,variant) DO UPDATE SET quantity=excluded.quantity", (printing_id, variant, quantity))
        return quantity

    def variants(self, printing_id: str) -> list[str]:
        card = self.cards.get(printing_id)["card"]
        variants = [key for key, available in card.get("variants", {}).items() if available is True]
        with closing(self.cards.connect()) as db:
            saved = [row[0] for row in db.execute("SELECT variant FROM collection WHERE printing_id=?", (printing_id,))]
        return list(dict.fromkeys(["unspecified", *variants, *saved]))

    def coverage(self) -> dict:
        with closing(self.cards.connect()) as db:
            count = db.execute("SELECT count(*) FROM cards WHERE standard=1 AND game='tcg'").fetchone()[0]
        return {"standard_printings": count, **self.cards.status()}

    def setting(self, key: str, value: str | None = None) -> str | None:
        with closing(self.cards.connect()) as db, db:
            if value is not None:
                db.execute("INSERT OR REPLACE INTO app_settings VALUES (?,?)", (key, value))
                return value
            row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
            return row[0] if row else None
