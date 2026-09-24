"""Read-only providers. No user-supplied URLs, secrets, or silent offline fallback."""
import json
import re
from datetime import datetime, timezone
from importlib.resources import files
from typing import Protocol

import httpx
from urllib.parse import quote

BASE_URL = "https://api.tcgdex.net/v2/en/cards"


class CardLookupError(ValueError):
    pass


class CardProvider(Protocol):
    def get(self, card_id: str, include_image: bool = False) -> dict: ...
    def search(self, query: str, page: int, page_size: int, include_image: bool = False, **filters) -> dict: ...


def check_id(card_id: str):
    if not isinstance(card_id, str) or len(card_id) > 80 or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.!?-]|%[0-9A-Fa-f]{2}){0,79}", card_id):
        raise CardLookupError("Use a TCGdex printing ID, e.g. sv02-097.")


def check_search(query: str, page: int, page_size: int, allow_empty=False):
    if not isinstance(query, str) or (not query.strip() and not allow_empty) or len(query) > 100 or type(page) is not int or type(page_size) is not int or not 1 <= page <= 10000 or not 1 <= page_size <= 50:
        raise ValueError("Query must be 1-100 characters; page 1-10000; page_size 1-50.")


def public_card(value, include_image=False):
    """Recursively remove visual assets, including nested set/booster artwork.

    Unknown useful source fields remain stored and returned. Pricing and detailed
    finish variants are retained in SQLite but omitted from deckbuilding output.
    """
    if isinstance(value, dict):
        return {k: public_card(v, include_image) for k, v in value.items()
                if k not in ("pricing", "variants_detailed") and
                (include_image or not any(x in k.casefold() for x in ("image", "logo", "symbol", "artwork")))}
    if isinstance(value, list):
        return [public_card(v, include_image) for v in value]
    if not include_image and isinstance(value, str) and value.startswith("https://assets.tcgdex.net/"):
        return None
    return value


def summary(card, include_image=False):
    keys = ("id", "name", "localId", "category", "hp", "types", "stage", "suffix", "trainerType", "energyType", "rarity", "regulationMark", "legal")
    result = {k: card[k] for k in keys if k in card}
    if isinstance(card.get("set"), dict):
        result["set"] = {k: card["set"][k] for k in ("id", "name") if k in card["set"]}
    if include_image and card.get("image"):
        result["image"] = card["image"]
    return result


class SnapshotCards:
    def __init__(self):
        payload = json.loads(files("tcg_lab").joinpath("data/cards.json").read_text(encoding="utf-8"))
        self.cards = {c["id"]: c for c in payload["cards"]}
        self.fetched_at = payload["fetched_at"]

    def get(self, card_id: str, include_image=False) -> dict:
        check_id(card_id)
        if card_id not in self.cards:
            raise CardLookupError(f"Card {card_id} is not in the bundled snapshot. Sync the card database and select sqlite mode, or choose a snapshot ID.")
        return {"card": public_card(self.cards[card_id], include_image), "source": "TCGdex bundled snapshot", "fetched_at": self.fetched_at,
                "source_url": f"{BASE_URL}/{card_id}", "live": False}

    def search(self, query: str, page: int = 1, page_size: int = 20, include_image=False, **filters) -> dict:
        if any(v is not None for v in filters.values()):
            # Reuse exactly the production search semantics with an isolated database.
            from tempfile import TemporaryDirectory
            from pathlib import Path
            from .card_db import SQLiteCards
            with TemporaryDirectory() as directory:
                db = SQLiteCards(Path(directory) / "snapshot.sqlite3")
                for card in self.cards.values():
                    db.put(card, fetched_at=self.fetched_at)
                result = db.search(query, page, page_size, include_image, **filters)
                result.update(scope="bundled snapshot only", fetched_at=self.fetched_at)
                result.pop("sync", None)
                return result
        check_search(query, page, page_size)
        matches = sorted((c for c in self.cards.values() if query.casefold() in c["name"].casefold() or query == c["id"]), key=lambda c: c["id"])
        start = (page - 1) * page_size
        return {"cards": [summary(c, include_image) for c in matches[start:start + page_size]],
                "page": page, "page_size": page_size, "total": len(matches),
                "scope": "bundled snapshot only", "fetched_at": self.fetched_at}


class LiveCards:
    def __init__(self, transport=None):
        self.transport = transport

    def _request(self, path: str = "", params=None):
        try:
            with httpx.Client(timeout=15, transport=self.transport, follow_redirects=False) as client:
                response = client.get(BASE_URL + path, params=params)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CardLookupError("TCGdex lookup failed (missing card, rate limit, or network error). Retry or use snapshot mode.") from exc

    def get(self, card_id: str, include_image=False) -> dict:
        check_id(card_id)
        card = self._request("/" + quote(card_id, safe=""))
        if not isinstance(card, dict) or card.get("id") != card_id or not card.get("name") or not card.get("category"):
            raise CardLookupError("TCGdex returned an incomplete card record.")
        # Pricing is outside the purpose of this tool.
        card = public_card(card, include_image)
        return {"card": card, "source": "TCGdex", "source_url": f"{BASE_URL}/{card_id}",
                "fetched_at": datetime.now(timezone.utc).isoformat(), "live": True}

    def search(self, query: str, page: int = 1, page_size: int = 20, include_image=False, **filters) -> dict:
        if any(v is not None for v in filters.values()):
            raise ValueError("Advanced filters require the local SQLite source; run sync and set TCG_CARD_SOURCE=sqlite.")
        check_search(query, page, page_size)
        cards = self._request(params={"name": "like:" + query.strip(), "pagination:page": page,
                                      "pagination:itemsPerPage": page_size})
        if not isinstance(cards, list):
            raise CardLookupError("TCGdex returned an invalid search response.")
        return {"cards": [summary(c, include_image) for c in cards], "page": page, "page_size": page_size, "scope": "TCGdex name search; may include Pocket",
                "next_page": page + 1 if len(cards) == page_size else None}
