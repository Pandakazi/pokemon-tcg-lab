"""Normalize Play! Limitless evidence and compute statistics locally.

Only fully resolved, 60-card submitted lists enter the denominator. That avoids
treating unknown printing mappings as evidence that a card was absent. This is
a cached sample of Play! Limitless events, not a census of paper tournaments.
"""
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import re
import time
import threading

import httpx

from .engine import PokeLabEngine, normalized_name

API = "https://play.limitlesstcg.com/api"


def utc_date(value: str) -> datetime:
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date.astimezone(timezone.utc)


class Analytics:
    def __init__(self, engine: PokeLabEngine):
        self.engine = engine
        with closing(engine.cards.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,name TEXT NOT NULL,date TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,source TEXT NOT NULL,raw TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tournament_decks (
                    id TEXT PRIMARY KEY,event_id TEXT NOT NULL,player TEXT NOT NULL,
                    placing INTEGER,archetype_id TEXT NOT NULL,archetype_name TEXT NOT NULL,
                    resolved INTEGER NOT NULL,raw TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS deck_event ON tournament_decks(event_id);
                CREATE TABLE IF NOT EXISTS tournament_cards (
                    deck_id TEXT NOT NULL,functional_id TEXT NOT NULL,count INTEGER NOT NULL,
                    PRIMARY KEY(deck_id,functional_id));
                CREATE INDEX IF NOT EXISTS analytics_card ON tournament_cards(functional_id,deck_id);
                CREATE INDEX IF NOT EXISTS events_date ON events(date);
            """)

    def resolver(self) -> tuple[dict, dict]:
        """Build local indexes once per refresh, not once per tournament card."""
        exact, names = {}, {}
        with closing(self.engine.cards.connect()) as db:
            for row in db.execute("SELECT c.id,c.name,c.number,c.set_id,s.raw set_raw,p.functional_id FROM cards c JOIN printing_identity p ON p.printing_id=c.id LEFT JOIN sets s ON s.id=c.set_id WHERE c.game='tcg'"):
                codes = [row["set_id"]]
                if row["set_raw"]:
                    metadata = json.loads(row["set_raw"])
                    codes.extend(code for code in (metadata.get("tcgOnline"), metadata.get("abbreviation", {}).get("official")) if isinstance(code, str))
                for code in codes:
                    exact.setdefault((code.upper(), row["number"].casefold().lstrip("0")), set()).add(row["functional_id"])
                names.setdefault(normalized_name(row["name"]), set()).add(row["functional_id"])
        return exact, names

    def remap_cached(self) -> int:
        """Re-resolve cached evidence after source text/set mappings change."""
        resolver = self.resolver()
        with closing(self.engine.cards.connect()) as db:
            events = db.execute("SELECT id,raw,fetched_at FROM events").fetchall()
            decks = db.execute("SELECT * FROM tournament_decks").fetchall()
        for event in events:
            standings = [{"player": row["id"].split(":", 1)[1], "name": row["player"], "placing": row["placing"],
                          "deck": {"id": row["archetype_id"], "name": row["archetype_name"]}, "decklist": json.loads(row["raw"])}
                         for row in decks if row["event_id"] == event["id"]]
            self.import_event(json.loads(event["raw"]), standings, resolver, fetched_at=event["fetched_at"])
        return len(events)

    def import_event(self, event: dict, standings: list, resolver=None, *, fetched_at=None) -> dict:
        if event.get("game") != "PTCG" or event.get("format") != "STANDARD":
            raise ValueError("Only PTCG Standard events are supported.")
        if event.get("bannedCards") or event.get("specialRules"):
            raise ValueError("Custom-rule events are excluded from Standard analytics.")
        event_id = str(event.get("id", ""))
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", event_id) or not isinstance(standings, list):
            raise ValueError("Invalid tournament response.")
        event_date = utc_date(event["date"])
        if event_date > datetime.now(timezone.utc):
            raise ValueError("Future events are not evidence yet.")
        exact, names = resolver or self.resolver()
        normalized = []
        for entry in standings:
            if not isinstance(entry, dict) or not entry.get("player") or not isinstance(entry.get("decklist"), dict):
                continue
            raw = entry["decklist"]
            cards = [c for group in ("pokemon", "trainer", "energy") for c in raw.get(group, [])]
            counts, total, resolved = Counter(), 0, True
            if not cards:
                continue
            for card in cards:
                if not isinstance(card, dict) or type(card.get("count")) is not int or not 1 <= card["count"] <= 60 or not isinstance(card.get("name"), str):
                    raise ValueError("Malformed decklist; previous event cache preserved.")
                total += card["count"]
                key = (str(card.get("set", "")).upper(), str(card.get("number", "")).casefold().lstrip("0"))
                candidates = exact.get(key) or names.get(normalized_name(card["name"]), set())
                if len(candidates) != 1:
                    resolved = False
                else:
                    counts[next(iter(candidates))] += card["count"]
            if total != 60:
                continue
            deck = entry.get("deck") or {}
            normalized.append((f"{event_id}:{entry['player']}", str(entry.get("name") or entry["player"]),
                               entry.get("placing"), str(deck.get("id") or "unknown"),
                               str(deck.get("name") or "Uncategorized"), resolved, raw, counts))
        with closing(self.engine.cards.connect()) as db, db:
            # Replace an event atomically; retries cannot double-count decklists.
            db.execute("DELETE FROM tournament_cards WHERE deck_id IN (SELECT id FROM tournament_decks WHERE event_id=?)", (event_id,))
            db.execute("DELETE FROM tournament_decks WHERE event_id=?", (event_id,))
            db.execute("INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?)", (event_id, str(event.get("name", event_id)), event_date.isoformat(), fetched_at or datetime.now(timezone.utc).isoformat(), f"https://play.limitlesstcg.com/tournament/{event_id}", json.dumps(event)))
            for deck_id, player, placing, archetype_id, archetype_name, resolved, raw, counts in normalized:
                db.execute("INSERT INTO tournament_decks VALUES (?,?,?,?,?,?,?,?)", (deck_id, event_id, player, placing, archetype_id, archetype_name, int(resolved), json.dumps(raw)))
                db.executemany("INSERT INTO tournament_cards VALUES (?,?,?)", [(deck_id, key, count) for key, count in counts.items()])
        return {"submitted": len(normalized), "resolved": sum(row[5] for row in normalized)}

    def period(self, days: int | None, now: datetime | None = None) -> tuple[str, str]:
        now = now or datetime.now(timezone.utc)
        if days is None:
            start = self.engine.setting("format_start")
            if not start:
                raise ValueError("Set the Current Format start date in Settings first.")
            start = utc_date(start)
        else:
            if days not in (7, 30, 60, 90):
                raise ValueError("Unsupported timeframe")
            start = now - timedelta(days=days)
        return start.isoformat(), now.isoformat()

    def stats(self, functional_id: str, days: int | None = 30, now=None) -> dict:
        start, end = self.period(days, now)
        with closing(self.engine.cards.connect()) as db:
            context = db.execute("SELECT COUNT(*) n, SUM(d.resolved) usable, COUNT(DISTINCT e.id) events,MIN(e.date) first,MAX(e.date) last FROM tournament_decks d JOIN events e ON e.id=d.event_id WHERE e.date BETWEEN ? AND ?", (start, end)).fetchone()
            sample = context["usable"] or 0
            matches = db.execute("SELECT COUNT(*) n,AVG(c.count) copies FROM tournament_cards c JOIN tournament_decks d ON d.id=c.deck_id JOIN events e ON e.id=d.event_id WHERE c.functional_id=? AND d.resolved=1 AND e.date BETWEEN ? AND ?", (functional_id, start, end)).fetchone()
            included = matches["n"]
            rows = db.execute("SELECT d.archetype_id,d.archetype_name,COUNT(*) n FROM tournament_cards c JOIN tournament_decks d ON d.id=c.deck_id JOIN events e ON e.id=d.event_id WHERE c.functional_id=? AND d.resolved=1 AND e.date BETWEEN ? AND ? GROUP BY d.archetype_id,d.archetype_name ORDER BY n DESC,d.archetype_id LIMIT 5", (functional_id, start, end)).fetchall()
            partners = db.execute("SELECT f.name,COUNT(*) n FROM tournament_cards a JOIN tournament_cards b ON a.deck_id=b.deck_id AND a.functional_id<>b.functional_id JOIN functional_cards f ON f.id=b.functional_id JOIN tournament_decks d ON d.id=a.deck_id JOIN events e ON e.id=d.event_id WHERE a.functional_id=? AND d.resolved=1 AND e.date BETWEEN ? AND ? GROUP BY b.functional_id ORDER BY n DESC,f.name LIMIT 5", (functional_id, start, end)).fetchall()
        return {"source": "Play! Limitless cached Standard submitted lists", "period_start": start, "period_end": end,
                "sample_size": sample, "included_decks": included,
                "usage_percent": round(100*included/sample, 2) if sample else None,
                "average_copies": round(matches["copies"], 2) if included else None,
                "events": context["events"], "observed_from": context["first"], "observed_to": context["last"],
                "excluded_unresolved": context["n"]-sample,
                "top_archetypes": [{"id": r[0], "name": r[1], "decks": r[2], "share_percent": round(100*r[2]/included, 2)} for r in rows],
                "pairings": [{"name": r[0], "decks": r[1]} for r in partners],
                "context": "Usage denominator: fully mapped submitted lists in cached events, not all players or all tournaments. Archetype share: decks including this functional card. No win-rate or causation claim."}

    def drilldown(self, functional_id: str, archetype_id: str, days: int | None = 30, now=None) -> list[dict]:
        start, end = self.period(days, now)
        with closing(self.engine.cards.connect()) as db:
            rows = db.execute("SELECT d.player,d.placing,d.raw,d.archetype_name,e.name event,e.date,e.source FROM tournament_cards c JOIN tournament_decks d ON d.id=c.deck_id JOIN events e ON e.id=d.event_id WHERE c.functional_id=? AND d.archetype_id=? AND d.resolved=1 AND e.date BETWEEN ? AND ? ORDER BY e.date DESC,d.placing LIMIT 200", (functional_id, archetype_id, start, end)).fetchall()
        return [{**dict(row), "cards": json.loads(row["raw"])} for row in rows]


class LimitlessClient:
    """Public supported API, deliberately paced; 429 errors never discard cache."""
    def __init__(self, client=None, delay=6.1, cancel_event=None):
        self.client = client or httpx.Client(timeout=30, follow_redirects=False)
        self.owns_client = client is None
        self.delay = delay
        self.last_request = 0.0
        self.cancel_event = cancel_event or threading.Event()

    def wait(self, seconds):
        if self.cancel_event.wait(max(0, seconds)):
            raise InterruptedError("Refresh canceled. Previously cached evidence is preserved.")

    def get(self, path: str, **params):
        for attempt in range(3):
            self.wait(self.delay-(time.monotonic()-self.last_request))
            self.last_request = time.monotonic()
            response = self.client.get(API + path, params=params)
            if response.status_code == 429:
                if attempt == 2:
                    raise ValueError("Limitless rate limit reached. Cached evidence is preserved; retry later.")
                try:
                    wait = float(response.headers.get("Retry-After", "30"))
                except ValueError:
                    wait = 30
                if wait > 60:
                    raise ValueError(f"Limitless asks you to wait {int(wait)} seconds before refreshing again.")
                self.wait(max(1, wait))
                continue
            response.raise_for_status()
            if response.headers.get("X-RateLimit-Remaining") == "0":
                self.last_request = time.monotonic()+60
            return response.json()
        raise ValueError("Limitless is unavailable")

    def refresh(self, analytics: Analytics, days=90, max_events=25, progress=print) -> dict:
        if not 1 <= max_events <= 1000 or not 1 <= days <= 365:
            raise ValueError("Invalid refresh bounds")
        cutoff = datetime.now(timezone.utc)-timedelta(days=days)
        resolver = analytics.resolver()
        imported = skipped = 0
        try:
            for page in range(1, 101):
                events = self.get("/tournaments", game="PTCG", format="STANDARD", limit=50, page=page)
                if not isinstance(events, list):
                    raise ValueError("Unexpected Limitless tournament response")
                if not events:
                    break
                for event in events:
                    event_date = utc_date(event["date"])
                    if event_date < cutoff:
                        return {"imported": imported, "skipped": skipped, "event_cap": max_events, "days": days}
                    if event_date > datetime.now(timezone.utc):
                        continue
                    event_id = str(event["id"])
                    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", event_id):
                        raise ValueError("Invalid Limitless event ID")
                    with closing(analytics.engine.cards.connect()) as db:
                        cached = db.execute("SELECT fetched_at FROM events WHERE id=?", (event_id,)).fetchone()
                    if cached and utc_date(cached[0]) > datetime.now(timezone.utc)-timedelta(hours=24):
                        imported += 1
                        if imported >= max_events:
                            return {"imported": imported, "skipped": skipped, "event_cap": max_events, "days": days}
                        continue
                    details = self.get(f"/tournaments/{event_id}/details")
                    if not details.get("decklists") or details.get("bannedCards") or details.get("specialRules"):
                        skipped += 1
                        continue
                    standings = self.get(f"/tournaments/{event_id}/standings")
                    if not standings or not all(isinstance(row.get("placing"), int) for row in standings):
                        skipped += 1  # In-progress/unpublished results are not final evidence.
                        continue
                    analytics.import_event(details, standings, resolver)
                    imported += 1
                    progress(f"Limitless: {imported}/{max_events} events cached")
                    if imported >= max_events:
                        return {"imported": imported, "skipped": skipped, "event_cap": max_events, "days": days}
            return {"imported": imported, "skipped": skipped, "event_cap": max_events, "days": days}
        finally:
            if self.owns_client:
                self.client.close()
