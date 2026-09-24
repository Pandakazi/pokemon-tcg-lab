"""Explicit, resumable TCGdex sync. No images are downloaded."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from urllib.parse import quote

from dotenv import load_dotenv
import httpx

from .card_db import SQLiteCards, parse_card, utcnow
from .cards import BASE_URL, CardLookupError, check_id


class SyncError(RuntimeError):
    pass


def request(client, url, *, headers=None, sleep=time.sleep):
    for attempt in range(3):
        try:
            response = client.get(url, headers=headers or {})
            if response.status_code == 304:
                return response
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            return response
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            retryable = not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code == 429 or exc.response.status_code >= 500
            if attempt == 2 or not retryable:
                raise SyncError("TCGdex is unavailable or returned an error. Existing cached records are preserved; rerun sync later.") from exc
            retry_after = exc.response.headers.get("Retry-After", "") if isinstance(exc, httpx.HTTPStatusError) else ""
            delay = min(float(retry_after), 30) if retry_after.isdigit() else 2 ** attempt
            sleep(delay)
    raise AssertionError("unreachable")


def synchronize(cards, *, client=None, workers=4, max_age_days=7, refresh=False, progress=print):
    """Upsert individually so interruption retains progress; never delete on failure.

    A separate SQLite lock prevents overlapping syncs and releases on process exit.
    HTTP validators are honored for stale rows; --refresh bypasses age skipping.
    """
    if not 1 <= workers <= 8 or max_age_days < 0:
        raise ValueError("workers must be 1-8; max_age_days must be nonnegative")
    with closing(sqlite3.connect(str(cards.path) + ".sync-lock.sqlite3", timeout=0)) as lock:
        try:
            lock.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            raise SyncError("Another card sync is already running; wait for it to finish.") from exc
        try:
            if client is None:
                with httpx.Client(timeout=30, follow_redirects=False, limits=httpx.Limits(max_connections=workers),
                                  headers={"User-Agent": "pokemon-tcg-lab/1 card-sync"}) as http:
                    return _sync(cards, http, workers, max_age_days, refresh, progress)
            return _sync(cards, client, workers, max_age_days, refresh, progress)
        except KeyboardInterrupt:
            report = cards.metadata("last_sync") or {}
            report.update(status="interrupted", interrupted_at=utcnow())
            cards.metadata("last_sync", report)
            raise


def _sync(cards, client, workers, max_age_days, refresh, progress):
    started = utcnow()
    try:
        index = request(client, BASE_URL).json()
        if not isinstance(index, list) or not index:
            raise ValueError("Empty or invalid catalog")
        ids = []
        for brief in index:
            if not isinstance(brief, dict):
                raise ValueError("Invalid index entry")
            check_id(brief.get("id", ""))
            ids.append(brief["id"])
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate printing IDs")
    except (ValueError, SyncError) as exc:
        cards.metadata("last_attempt", {"status": "failed", "started_at": started})
        raise SyncError("Could not read the TCGdex catalog. Existing database is unchanged; retry sync when online.") from exc
    previous = cards.cached()
    report = {"status": "running", "started_at": started, "catalog": len(ids),
              "updated": 0, "unchanged": 0, "skipped": 0, "failed": 0, "missing": 0}
    cards.metadata("last_sync", report)
    progress(f"TCGdex catalog: {len(ids)} printings. Fetching set metadata (no images)...")
    # Set series distinguishes Pocket without guessing from card names or legality.
    set_ids = sorted({card_id.rsplit("-", 1)[0] for card_id in ids})
    failed_sets = set()

    def fetch_set(set_id):
        try:
            record = request(client, BASE_URL.rsplit("/", 1)[0] + "/sets/" + quote(set_id, safe="")).json()
            if not isinstance(record, dict) or record.get("id") != set_id:
                raise ValueError("Mismatched set")
            cards.put_set(record)
            return set_id, None
        except (ValueError, SyncError) as exc:
            return set_id, str(exc)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for set_id, error in pool.map(fetch_set, set_ids):
            if error:
                failed_sets.add(set_id)
    threshold = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    pending = []
    for card_id in ids:
        cached = previous.get(card_id)
        if card_id.rsplit("-", 1)[0] in failed_sets:
            report["failed"] += 1
        elif cached and not refresh and datetime.fromisoformat(cached["checked_at"]) >= threshold:
            report["skipped"] += 1
        else:
            pending.append(card_id)
    progress(f"Downloading/checking {len(pending)} cards; {report['skipped']} recently checked cards skipped. You may stop and rerun to resume.")

    def fetch_card(card_id):
        cached = previous.get(card_id)
        headers = {}
        if cached:
            if cached["etag"]:
                headers["If-None-Match"] = cached["etag"]
            elif cached["modified"]:
                headers["If-Modified-Since"] = cached["modified"]
        try:
            response = request(client, BASE_URL + "/" + quote(card_id, safe=""), headers=headers)
            if response.status_code == 304:
                if not cached:
                    raise ValueError("304 without a cached record")
                cards.touch(card_id)
                return "unchanged"
            record = parse_card(response.json(), card_id)
            cards.put(record, etag=response.headers.get("etag"), modified=response.headers.get("last-modified"))
            return "updated"
        except (ValueError, SyncError):
            return "failed"

    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        completed = 0
        for offset in range(0, len(pending), 100):
            # Bound queued tasks so Ctrl+C can cancel rather than drain the catalog.
            for outcome in pool.map(fetch_card, pending[offset:offset + 100]):
                completed += 1
                report[outcome] += 1
                if completed % 250 == 0 or completed == len(pending):
                    cards.metadata("last_sync", report)
                    progress(f"Cards {completed}/{len(pending)}; updated {report['updated']}, unchanged {report['unchanged']}, failed {report['failed']}")
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
    present = cards.cached()
    report["missing"] = len(set(ids) - present.keys())
    report["retained_unlisted"] = len(present.keys() - set(ids))
    report["finished_at"] = utcnow()
    report["status"] = "complete" if report["failed"] == 0 and report["missing"] == 0 else "partial"
    cards.metadata("last_sync", report)
    if report["status"] == "complete":
        cards.metadata("last_complete_sync", report["finished_at"])
    return report


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Download/update the local English TCGdex card database. No image downloads.")
    parser.add_argument("--db", default=os.getenv("TCG_CARDS_DB_PATH", "data/cards.sqlite3"))
    parser.add_argument("--refresh", action="store_true", help="Recheck every card now, including recently checked cards (use after rotations).")
    parser.add_argument("--max-age-days", type=int, default=7, help="Recheck existing cards after this many days (default 7).")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent requests, 1-8 (default 4).")
    parser.add_argument("--status", action="store_true", help="Show local database status without network access.")
    args = parser.parse_args()
    try:
        cards = SQLiteCards(Path(args.db))
        if args.status:
            print(json.dumps(cards.status(), indent=2))
            return 0
        report = synchronize(cards, workers=args.workers, max_age_days=args.max_age_days,
                             refresh=args.refresh, progress=lambda message: print(message, flush=True))
        print(json.dumps(report, indent=2))
        if report["status"] != "complete":
            print("Sync is partial. Cached cards still work. Rerun this command to retry; --refresh also retries stale existing records.")
            return 1
        print("Card database ready. Use TCG_CARD_SOURCE=sqlite in .env and restart the server if you changed that setting.")
        return 0
    except (SyncError, CardLookupError, ValueError, OSError, sqlite3.Error) as exc:
        print(f"Card sync could not finish: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nSync stopped. Downloaded cards are saved; rerun the same command to resume.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
