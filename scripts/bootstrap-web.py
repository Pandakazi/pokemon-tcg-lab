"""Compose existing database/index initializers; never request a provider key."""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]


def copy_cache(source, target, *, cards=False):
    if target.exists() or not source:
        return
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError(f"Cached database not found: {source}")
    # Read-only SQLite backup supports a cache that is currently open elsewhere.
    temporary = target.with_suffix('.bootstrap.tmp')
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
            with closing(sqlite3.connect(temporary)) as dst:
                src.backup(dst)
                if cards:
                    # Only the new cache copy: do not import someone's Qt collection.
                    dst.execute('DROP TABLE IF EXISTS collection')
                    dst.commit()
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(args):
    from tcg_lab.card_db import SQLiteCards
    from tcg_lab.cards import CardLookupError
    from pokelab.api import ReadOnlyCards
    from pokelab.collection import Collection
    from pokelab.competitive import Competitive
    from pokelab.decks import Decks

    data = ROOT / 'data'
    data.mkdir(exist_ok=True)
    (ROOT / '.cache/local-web').mkdir(parents=True, exist_ok=True)
    path = data / 'cards.sqlite3'
    if args.offline and not path.exists() and not args.cards_database:
        raise ValueError('Offline setup needs a populated card cache. Supply -CardsDatabase C:\\path\\cards.sqlite3, or rerun setup online.')
    copy_cache(args.cards_database, path, cards=True)
    cards = SQLiteCards(path)  # Existing offline gameplay/format index preparation.
    if not cards.status()['cards']:
        if args.offline:
            raise ValueError('Offline setup needs a populated card cache. Supply -CardsDatabase C:\\path\\cards.sqlite3, or rerun setup online.')
        from tcg_lab.sync_cards import synchronize
        print('Downloading the English TCGdex card catalog. This can take several minutes.', flush=True)
        result = synchronize(cards)
        if result.get('missing') or not cards.status()['cards']:
            raise ValueError('Card download is incomplete. Rerun setup when online.')
    elif (cards.metadata('last_sync') or {}).get('missing'):
        if args.offline:
            raise ValueError('The card cache has an incomplete sync. Rerun setup online to resume it.')
        from tcg_lab.sync_cards import synchronize
        result = synchronize(cards)
        if result.get('missing'):
            raise ValueError('Card download is incomplete. Rerun setup when online.')
    readonly = ReadOnlyCards(path)
    collection = Collection(readonly, data / 'user-state.sqlite3')
    collection.initialize()
    competitive_path = data / 'competitive.sqlite3'
    copy_cache(args.competitive_database, competitive_path)
    Competitive(readonly, competitive_path).initialize()
    decks = Decks(collection, data / 'deck-workspace.sqlite3')
    with closing(decks.connect()) as db, db:
        decks.initialize(db)
    print(f"Local databases and indexes ready ({cards.status()['cards']} cached cards).", flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cards-database')
    parser.add_argument('--competitive-database')
    parser.add_argument('--offline', action='store_true')
    try:
        prepare(parser.parse_args())
    except Exception as error:
        print(f'Local data preparation: {error}', file=sys.stderr)
        sys.exit(1)
