"""Shared legacy deck-engine composition, independent of any transport."""
import os
from .cards import LiveCards, SnapshotCards
from .card_db import SQLiteCards
from .service import Lab
from .store import DeckStore


def create_lab(source: str | None = None) -> Lab:
    source = source or os.getenv("TCG_CARD_SOURCE", "sqlite")
    providers = {"live": LiveCards, "snapshot": SnapshotCards,
                 "sqlite": lambda: SQLiteCards(os.getenv("TCG_CARDS_DB_PATH", "data/cards.sqlite3"))}
    if source not in providers:
        raise ValueError("TCG_CARD_SOURCE must be sqlite, snapshot or live.")
    return Lab(providers[source](), DeckStore(os.getenv("TCG_DB_PATH", "data/decks.sqlite3")))
