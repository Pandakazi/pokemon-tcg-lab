from collections import Counter
from math import comb

from .cards import CardLookupError, CardProvider
from .models import Deck
from .store import DeckStore


class Lab:
    def __init__(self, cards: CardProvider, store: DeckStore):
        self.cards, self.store = cards, store

    def validate(self, deck: Deck, *, require_complete: bool = True) -> dict:
        counts = deck.counts()
        total = sum(counts.values())
        errors, unknown = [], []
        sources = {}
        by_name, categories = Counter(), Counter()
        basic, ace_spec = 0, 0
        if total > 60 or (require_complete and total != 60):
            errors.append(f"Deck contains {total} cards; exactly 60 are required.")
        for card_id, count in counts.items():
            try:
                record = self.cards.get(card_id)
            except CardLookupError as exc:
                unknown.append(f"{card_id}: {exc}")
                continue
            card = record["card"]
            source = sources.setdefault(record["source"], {"cards": 0, "fetched_at_min": record["fetched_at"], "fetched_at_max": record["fetched_at"]})
            source["cards"] += 1
            source["fetched_at_min"] = min(source["fetched_at_min"], record["fetched_at"])
            source["fetched_at_max"] = max(source["fetched_at_max"], record["fetched_at"])
            if record.get("game") == "pocket":
                errors.append(f"{card_id}: Pokemon TCG Pocket cards cannot be used in a physical TCG deck.")
            category = card.get("category")
            categories[category or "Unknown"] += count
            if category not in ("Pokemon", "Trainer", "Energy"):
                unknown.append(f"{card_id}: unsupported category.")
            if category == "Pokemon":
                if not card.get("stage"):
                    unknown.append(f"{card_id}: missing evolution stage.")
                elif card["stage"] == "Basic":
                    basic += count
            unlimited_energy = category == "Energy" and card.get("energyType") == "Normal"
            if not unlimited_energy:
                by_name[card["name"].casefold()] += count
            if category == "Energy" and card.get("energyType") not in ("Normal", "Special"):
                unknown.append(f"{card_id}: missing energy type; copy limit needs review.")
            if "ACE SPEC" in card.get("rarity", "").upper():
                ace_spec += count
            elif not card.get("rarity"):
                unknown.append(f"{card_id}: rarity missing; ACE SPEC status needs review.")
            legality = card.get("legal", {}).get(deck.format)
            if deck.format == "unlimited":
                unknown.append(f"{card_id}: Unlimited legality is not supplied by this provider.")
            elif legality is False:
                errors.append(f"{card_id} ({card['name']}): provider reports not legal in {deck.format}.")
            elif legality is not True:
                unknown.append(f"{card_id}: no {deck.format} legality supplied (possibly a Pocket card).")
        for name, count in sorted(by_name.items()):
            if count > 4:
                errors.append(f"{name}: {count} copies across printings; normal limit is 4.")
        if ace_spec > 1:
            errors.append(f"Deck has {ace_spec} ACE SPEC cards; limit is 1.")
        if basic == 0:
            if unknown:
                unknown.append("Could not establish whether the deck has a Basic Pokemon.")
            else:
                errors.append("Deck must contain at least one Basic Pokemon.")
        return {"status": "invalid" if errors else "incomplete" if unknown else "passes_supported_checks",
                "total_cards": total, "basic_pokemon": basic, "ace_spec_count": ace_spec,
                "categories": dict(categories), "errors": errors, "unknown": unknown,
                "format": deck.format, "tournament_legal": None,
                "limitations": ["Checks 60 cards, normal four-copy rule across printings, Basic Pokemon, ACE SPEC count, and provider format flags.",
                                "Not tournament certification: card-specific deck rules, historical rulings, reprint equivalence and bans need independent verification.",
                                "Provider legality can be stale; bundled snapshots are dated and never represent a live rules check."],
                "sources": sources}

    def save(self, deck: Deck, allow_invalid: bool = False) -> dict:
        result = self.validate(deck)
        if result["errors"] and not allow_invalid:
            return {"saved": False, "validation": result,
                    "message": "Fix the errors, or explicitly set allow_invalid=true to save a draft."}
        return {"saved": True, **self.store.save(deck, result)}

    def compare(self, name: str, from_version: str, to_version: str) -> dict:
        before = Deck.model_validate(self.store.get(name, from_version)["deck"])
        after = Deck.model_validate(self.store.get(name, to_version)["deck"])
        a, b = before.counts(), after.counts()
        return {"name": after.name, "from_version": before.version, "to_version": after.version,
                "from_format": before.format, "to_format": after.format,
                "changes": [{"card_id": key, "before": a.get(key, 0), "after": b.get(key, 0),
                             "delta": b.get(key, 0) - a.get(key, 0)}
                            for key in sorted(a.keys() | b.keys()) if a.get(key, 0) != b.get(key, 0)],
                "total_before": sum(a.values()), "total_after": sum(b.values())}

    def analyze(self, deck: Deck) -> dict:
        validation = self.validate(deck)
        total, basic = validation["total_cards"], validation["basic_pokemon"]
        # Unconditional random opening seven, before mulligans or prizes are drawn.
        probability = None
        if total >= 7 and not validation["unknown"]:
            probability = 1 - (comb(total - basic, 7) if total - basic >= 7 else 0) / comb(total, 7)
        return {"name": deck.name, "version": deck.version, "validation": validation,
                "unique_printings": len(deck.counts()),
                "opening_hand": {"size": 7, "probability_at_least_one_basic": probability,
                                 "mulligan_probability": None if probability is None else 1 - probability,
                                 "assumption": "Uniform random seven-card hand before mulligans; not a match win probability."},
                "notes": "V0 reports composition and opening Basic probability. It does not infer matchup strength, search/draw outs, or simulate card effects."}
