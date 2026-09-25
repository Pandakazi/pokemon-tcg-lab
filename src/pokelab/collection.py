"""Single-user local state, canonical identities and read-only card catalogue.

Schema v1 reuses exact-variation collection rows. First initialization copies legacy
Qt ownership once, transactionally; the source cache is never modified or deleted.
"""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
from threading import RLock

from .engine import functional_signature
from .library_identity import library_signature, basic_image_priority, REPRESENTATIVE_ORDER_SQL
from .images import TCGdexImages
from .quantities import COLLECTION_SCHEMA, read_quantity, write_quantity, variant_names


def identity(signature):
    return hashlib.sha256(signature.encode()).hexdigest()[:32]


def representative_printings(cards, functional_ids, catalog=None):
    """Read-only artwork resolution using canonical IDs and Library ranking.

    Image eligibility is applied before representative choice. Curated Basic
    Energy may use its existing Library presentation group; no IDs, quantities,
    finish preferences or collection rows are changed.
    """
    wanted = set(functional_ids)
    if not wanted: return {}
    records = catalog[0] if catalog else None
    references, basic_groups, basic_images = {}, {}, {}
    images = TCGdexImages()
    with closing(cards.connect()) as db:
        db.create_function('basic_image_priority',1,lambda raw:basic_image_priority(json.loads(raw)),deterministic=True)
        rows = db.execute(f'''SELECT c.id,c.raw FROM cards c LEFT JOIN sets s ON s.id=c.set_id
            WHERE c.game='tcg' AND c.standard=1 ORDER BY {REPRESENTATIVE_ORDER_SQL}''')
        for row in rows:
            record = records.get(row['id']) if records else None
            raw = record['card'] if record else json.loads(row['raw'])
            fid = record['functional_id'] if record else identity(functional_signature(raw))
            library_key = library_signature(raw)
            image_url = images.url(raw,large=True)
            reference = dict(name=raw['name'],printing_id=raw['id'],image_url=image_url)
            basic = library_key.startswith('library-basic-energy:')
            if basic and image_url: basic_images.setdefault(library_key,reference)
            if fid not in wanted: continue
            if basic: basic_groups[fid] = library_key
            if fid not in references or (not references[fid]['image_url'] and image_url):
                references[fid] = reference
    for fid,key in basic_groups.items():
        if not references[fid]['image_url'] and key in basic_images:
            references[fid] = basic_images[key]
    return references


class Collection:
    def __init__(self, cards, path):
        self.cards, self.path = cards, Path(path).resolve()
        if self.path == cards.path:
            raise ValueError('User-state storage must be separate from the card cache.')
        self._lock = RLock()
        self._stamp = None
        self._ready = False

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def initialize(self):
        with self._lock:
            if self._ready:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with closing(self.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                version = db.execute('PRAGMA user_version').fetchone()[0]
                if version not in (0,1):
                    raise ValueError('Unsupported user-state schema; preserve this database and upgrade PokéLab.')
                if version == 0:
                    db.execute(COLLECTION_SCHEMA)
                    db.execute('CREATE TABLE IF NOT EXISTS library_preferences (library_id TEXT PRIMARY KEY,printing_id TEXT NOT NULL,variant TEXT NOT NULL)')
                    with closing(self.cards.connect()) as source:
                        if source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='collection'").fetchone():
                            for row in source.execute('SELECT printing_id,variant,quantity FROM collection'):
                                # Existing state wins; restarting cannot resurrect old ownership.
                                db.execute('INSERT OR IGNORE INTO collection VALUES (?,?,?)', tuple(row))
                    db.execute('PRAGMA user_version=1')
            self._ready = True

    def catalog(self):
        with self._lock:
            stamp = (self.cards.path.stat().st_mtime_ns, self.cards.path.stat().st_size)
            if stamp != self._stamp:
                records, functions, libraries = {}, {}, {}
                with closing(self.cards.connect()) as db:
                    self.cards._ready(db)
                    for row in db.execute('SELECT id,raw,game,checked_at FROM cards'):
                        raw = json.loads(row['raw'])
                        fid, lid = identity(functional_signature(raw)), identity(library_signature(raw))
                        records[row['id']] = {'card': raw, 'functional_id': fid, 'library_id': lid,
                                              'game': row['game'], 'checked_at': row['checked_at']}
                        functions.setdefault(fid, []).append(row['id'])
                        libraries.setdefault(lid, []).append(row['id'])
                self._records, self._functions, self._libraries, self._stamp = records, functions, libraries, stamp
            return self._records, self._functions, self._libraries

    def snapshot(self):
        records, functions, libraries = self.catalog()
        self.initialize()
        with closing(self.connect()) as db:
            quantities = {(r['printing_id'],r['variant']): r['quantity'] for r in db.execute('SELECT * FROM collection')}
            preferences = {r['library_id']: (r['printing_id'],r['variant']) for r in db.execute('SELECT * FROM library_preferences')}
        functional_totals, library_totals = {}, {}
        for (id, _), n in quantities.items():
            if id in records:
                for key, totals in [('functional_id',functional_totals),('library_id',library_totals)]:
                    group = records[id][key]; totals[group] = totals.get(group,0) + n
        return CollectionSnapshot(records, functions, libraries, quantities, preferences, functional_totals, library_totals)

    def update(self, printing_id, variant, *, quantity=None, delta=None):
        snapshot = self.snapshot()
        snapshot.validate_variant(printing_id, variant)
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            current = read_quantity(db, printing_id, variant)
            value = quantity if quantity is not None else max(0, current + delta)
            write_quantity(db, printing_id, variant, value)
        return self.snapshot().ownership(printing_id, variant)

    def prefer(self, anchor, printing_id, variant):
        snapshot = self.snapshot()
        snapshot.validate_variant(printing_id, variant)
        if snapshot.records[anchor]['library_id'] != snapshot.records[printing_id]['library_id']:
            raise ValueError('Preferred printing must belong to this Library card.')
        with closing(self.connect()) as db, db:
            db.execute('INSERT INTO library_preferences VALUES (?,?,?) ON CONFLICT(library_id) DO UPDATE SET printing_id=excluded.printing_id,variant=excluded.variant',
                       (snapshot.records[anchor]['library_id'], printing_id, variant))
        return {'printing_id': printing_id, 'variant': variant}


class CollectionSnapshot:
    def __init__(self, records, functions, libraries, quantities, preferences, functional_totals, library_totals):
        self.records, self.functions, self.libraries = records, functions, libraries
        self.quantities, self.preferences = quantities, preferences
        self.functional_totals, self.library_totals = functional_totals, library_totals

    def variants(self, id):
        return variant_names(self.records[id]['card'], (v for (p,v) in self.quantities if p == id))

    def validate_variant(self, id, variant):
        if variant not in self.variants(id):
            raise ValueError('Unknown variation for this printing.')

    def presentation_variants(self, id):
        variants = self.variants(id)
        explicit = [v for v in variants if v != 'unspecified']
        return explicit or ['unspecified']

    def default_variant(self, id):
        variants = self.presentation_variants(id)
        return 'normal' if 'normal' in variants else variants[0]

    def ownership(self, id, variant):
        record = self.records[id]
        return {'functional_id': record['functional_id'], 'library_id': record['library_id'],
                'variant': variant, 'quantity': self.quantities.get((id,variant),0),
                'functional_total': self.functional_totals.get(record['functional_id'],0),
                'library_total': self.library_totals.get(record['library_id'],0)}

    def displayed(self, id):
        lid = self.records[id]['library_id']
        preferred = self.preferences.get(lid)
        if preferred and preferred[0] in self.records and self.records[preferred[0]]['library_id'] == lid and preferred[1] in self.variants(preferred[0]):
            return preferred
        return id, self.default_variant(id)
