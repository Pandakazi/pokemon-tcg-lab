"""Read-only providers. No user-supplied URLs, secrets, or silent offline fallback."""
import json
import re
from datetime import datetime, timezone
from importlib.resources import files
from typing import Protocol

import httpx

BASE_URL = "https://api.tcgdex.net/v2/en/cards"


class CardLookupError(ValueError):
    pass


class CardProvider(Protocol):
    def get(self, card_id: str) -> dict: ...
    def search(self, query: str, page: int, page_size: int) -> dict: ...


def check_id(card_id: str):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,79}", card_id):
        raise CardLookupError("Use a TCGdex printing ID, e.g. sv02-097.")


def check_search(query: str, page: int, page_size: int):
    if not query.strip() or len(query) > 100 or not 1 <= page <= 10000 or not 1 <= page_size <= 50:
        raise ValueError("Query must be 1-100 characters; page 1-10000; page_size 1-50.")


class SnapshotCards:
    def __init__(self):
        payload = json.loads(files("tcg_lab").joinpath("data/cards.json").read_text(encoding="utf-8"))
        self.cards = {c["id"]: c for c in payload["cards"]}
        self.fetched_at = payload["fetched_at"]

    def get(self, card_id: str) -> dict:
        check_id(card_id)
        if card_id not in self.cards:
            raise CardLookupError(f"Card {card_id} is not in the bundled snapshot. Enable live mode or choose a snapshot ID.")
        return {"card": self.cards[card_id], "source": "TCGdex bundled snapshot", "fetched_at": self.fetched_at,
                "source_url": f"{BASE_URL}/{card_id}", "live": False}

    def search(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        check_search(query, page, page_size)
        matches = sorted((c for c in self.cards.values() if query.casefold() in c["name"].casefold()), key=lambda c: c["id"])
        start = (page - 1) * page_size
        return {"cards": [{k: c[k] for k in ("id", "name")} for c in matches[start:start + page_size]],
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

    def get(self, card_id: str) -> dict:
        check_id(card_id)
        card = self._request("/" + card_id)
        if not isinstance(card, dict) or card.get("id") != card_id or not card.get("name") or not card.get("category"):
            raise CardLookupError("TCGdex returned an incomplete card record.")
        # Pricing is outside the purpose of this tool.
        card = {k: v for k, v in card.items() if k not in ("pricing", "variants_detailed")}
        return {"card": card, "source": "TCGdex", "source_url": f"{BASE_URL}/{card_id}",
                "fetched_at": datetime.now(timezone.utc).isoformat(), "live": True}

    def search(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        check_search(query, page, page_size)
        cards = self._request(params={"name": "like:" + query.strip(), "pagination:page": page,
                                      "pagination:itemsPerPage": page_size})
        if not isinstance(cards, list):
            raise CardLookupError("TCGdex returned an invalid search response.")
        return {"cards": cards, "page": page, "page_size": page_size, "scope": "TCGdex name search; may include Pocket",
                "next_page": page + 1 if len(cards) == page_size else None}
