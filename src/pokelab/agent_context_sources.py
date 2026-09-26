"""Request-local read transactions. Never create, initialize, migrate or repair."""
from contextlib import ExitStack, contextmanager
from pathlib import Path
import sqlite3

from .api import ReadOnlyCards
from .collection import Collection, CollectionSnapshot
from .competitive import Competitive


class Unavailable(ValueError):
    pass


class Lease:
    """Certified services may close leases; only the snapshot owner closes SQLite."""
    def __init__(self, db): self.db = db
    def __getattr__(self, key): return getattr(self.db, key)
    def close(self): pass


class SnapshotCards(ReadOnlyCards):
    def __init__(self, path, db):
        super().__init__(path)
        self.db = db
    def connect(self): return Lease(self.db)


class SnapshotCollection(Collection):
    def __init__(self, cards, path, db):
        super().__init__(cards, path)
        self.db = db
    def connect(self): return Lease(self.db)
    def initialize(self): raise Unavailable('Initialization is forbidden in Agent context.')
    def snapshot(self):
        records, functions, libraries = self.catalog()
        quantities = {(r['printing_id'], r['variant']): r['quantity'] for r in self.db.execute('SELECT * FROM collection')}
        if any(type(q) is not int or not 0 <= q <= 9999 for q in quantities.values()):
            raise Unavailable('Invalid collection quantities.')
        functional, library = {}, {}
        for (key, _), count in quantities.items():
            if key in records:
                for target, field in ((functional, 'functional_id'), (library, 'library_id')):
                    identity = records[key][field]
                    target[identity] = target.get(identity, 0) + count
        # Preferences are intentionally neither read nor exposed.
        return CollectionSnapshot(records, functions, libraries, quantities, {}, functional, library)


class SnapshotCompetitive(Competitive):
    def __init__(self, cards, path, db, format_start):
        super().__init__(cards, path, format_start)
        self.db = db
    def connect(self, write=False):
        if write: raise Unavailable('Writes are forbidden in Agent context.')
        return Lease(self.db)


def stamp(path):
    return tuple((str(p), p.stat().st_size, p.stat().st_mtime_ns) if p.exists() else (str(p), None, None)
                 for p in (path, Path(str(path)+'-wal'), Path(str(path)+'-journal')))


class Sources:
    """Host-supplied paths, never paths/SQL/URLs selected by the question."""
    def __init__(self, *, cards, collection, workspace, competitive, format_start=None):
        self.paths = {k: Path(v).resolve() for k,v in dict(cards=cards, collection=collection,
                        workspace=workspace, competitive=competitive).items()}
        if len(set(self.paths.values())) != 4:
            raise ValueError('All four stores must be explicitly distinct.')
        self.format_start = format_start

    @contextmanager
    def snapshot(self):
        versions = dict(cards=1, collection=1, workspace=2, competitive=0)
        tables = dict(cards=('cards','sets'), collection=('collection','library_preferences'),
                      workspace=('workspace','saved_decks','default_printings'),
                      competitive=('competitive_events','competitive_decks','competitive_pages','competitive_status'))
        before = {k: stamp(p) for k,p in self.paths.items()}
        with ExitStack() as stack:
            dbs, errors = {}, {}
            for key,path in self.paths.items():
                try:
                    db = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=5)
                    stack.callback(db.close)
                    db.row_factory = sqlite3.Row
                    db.execute('PRAGMA query_only=ON')
                    db.execute('BEGIN')
                    if db.execute('PRAGMA user_version').fetchone()[0] != versions[key]:
                        raise Unavailable('Incompatible schema; no migration attempted.')
                    found = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if not set(tables[key]).issubset(found): raise Unavailable('Required tables unavailable.')
                    dbs[key] = db
                except (sqlite3.Error, OSError, ValueError):
                    errors[key] = 'storage_unavailable_or_incompatible'
            yield dbs, errors
            if any(stamp(p) != before[k] for k,p in self.paths.items()):
                raise Unavailable('inconsistent_snapshot: source files changed during retrieval')
