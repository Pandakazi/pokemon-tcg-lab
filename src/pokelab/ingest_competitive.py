"""Explicit server/operator ingestion: python -m pokelab.ingest_competitive.

Fetches bounded, paced main-site pages only. No frontend refresh endpoint.
"""
import argparse
from datetime import datetime, timedelta, timezone
import os
import time
import httpx

from .api import ReadOnlyCards
from .competitive import Competitive
from .limitless_main import ORIGIN, parse_index, parse_results, parse_decklists, require


def refresh(store, *, days=90, max_events=25, client=None, delay=2.0, progress=print):
    if not 1 <= days <= 3650 or not 1 <= max_events <= 1000:
        raise ValueError('Invalid ingestion bounds')
    owned = client is None
    client = client or httpx.Client(timeout=60, follow_redirects=False, headers={'User-Agent':'PokeLab/Phase4 tournament-evidence'})
    last = 0.0
    def get(path):
        nonlocal last
        require(path.startswith('/tournaments'), 'unexpected source path')
        time.sleep(max(0, delay-(time.monotonic()-last)))
        last = time.monotonic()
        response = client.get(ORIGIN+path)
        response.raise_for_status()  # Including 429: stop, preserve existing evidence.
        require('text/html' in response.headers.get('content-type',''), 'expected HTML response')
        return response.text
    cutoff = datetime.now(timezone.utc).date()-timedelta(days=days-1)
    resolver = store.resolver()
    imported = mapped = published = 0
    try:
        page = 1
        while imported < max_events:
            index_path = f'/tournaments?page={page}'
            index_html = get(index_path)
            events, current, maximum = parse_index(index_html)
            require(current == page, 'pagination did not advance')
            for event in events:
                if event['date'] < cutoff.isoformat() or event['date'] > datetime.now(timezone.utc).date().isoformat() or event['format'] != 'standard': continue
                path = '/tournaments/'+event['id']
                results_html = get(path)
                results = parse_results(results_html)
                deck_path = path+'/decklists?lang=en&mode=regular'
                deck_html = get(deck_path)
                decks = parse_decklists(deck_html,results)
                report = store.import_event(event,decks,len(results),
                            {ORIGIN+index_path:index_html,ORIGIN+path:results_html,ORIGIN+deck_path:deck_html},resolver)
                imported += 1; mapped += report['mapped']; published += report['published']
                progress(f"{event['name']}: {report['mapped']}/{report['published']} mapped published lists")
                if imported >= max_events: break
            if page >= maximum or min(e['date'] for e in events) < cutoff.isoformat(): break
            page += 1
        store.record_status()
        return dict(events=imported,published=published,mapped=mapped)
    except Exception as error:
        store.record_status(f'{type(error).__name__}: {error}')
        raise
    finally:
        if owned: client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cards',default=os.getenv('TCG_CARDS_DB_PATH','data/cards.sqlite3'))
    parser.add_argument('--evidence',default=os.getenv('POKELAB_COMPETITIVE_DB_PATH'))
    parser.add_argument('--days',type=int,default=90)
    parser.add_argument('--max-events',type=int,default=25)
    parser.add_argument('--remap',action='store_true',help='Re-normalize cached evidence after card sync; no network')
    args = parser.parse_args()
    cards = ReadOnlyCards(args.cards)
    store = Competitive(cards,args.evidence or cards.path.with_name('competitive.sqlite3'))
    print(store.remap_cached() if args.remap else refresh(store,days=args.days,max_events=args.max_events))


if __name__ == '__main__': main()
