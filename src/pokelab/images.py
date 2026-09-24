"""Replaceable URL provider; Qt handles bounded, demand-loaded disk caching."""
from typing import Protocol
from urllib.parse import urlsplit


class CardImageProvider(Protocol):
    def url(self, card: dict, large: bool = False) -> str | None: ...


class TCGdexImages:
    def url(self, card: dict, large: bool = False) -> str | None:
        base = card.get("image")
        if not isinstance(base, str):
            return None
        parsed = urlsplit(base)
        if parsed.scheme != "https" or parsed.hostname != "assets.tcgdex.net" or parsed.username or parsed.query or parsed.fragment:
            return None
        return base.rstrip("/") + ("/high.webp" if large else "/low.webp")
