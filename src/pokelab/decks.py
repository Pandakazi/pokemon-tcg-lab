"""Persistent player-controlled decks; read-only adapters over certified identities.

No collection writes. Basic Energy uses the existing curated recognition rule,
but its deck key is deliberately separate from Library/canonical identity.
"""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from tcg_lab.cards import CardLookupError
from tcg_lab.models import Deck, DeckEntry
from tcg_lab.service import Lab
from .engine import normalized_name
from .library_identity import library_signature


def deck_identity(record):
    signature = library_signature(record['card'])
    if signature.startswith('library-basic-energy:'):
        return signature.replace('library-', 'deck-', 1)
    return record['functional_id']


class DeckCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[2]
    action: Literal['quantity', 'remove', 'default_printing', 'rename', 'save', 'new', 'open']
    revision: int = Field(ge=0, strict=True)
    printing_id: str | None = Field(None, min_length=1, max_length=100)
    identity: str | None = Field(None, min_length=1, max_length=100)
    variant: str | None = Field(None, min_length=1, max_length=100)
    delta: int | None = Field(None, strict=True, ge=-1, le=1)
    name: str | None = Field(None, min_length=1, max_length=100)
    deck_id: str | None = Field(None, min_length=1, max_length=100)
    discard: bool = False
    exact: bool = False


class DeckConflict(ValueError):
    pass


class DeckProvider:
    """Resolve functional deck keys independently of chosen presentation.

    A source-marked legal equivalent can establish legality for a historical
    presentation. No equivalence beyond existing signatures / curated Energy.
    """
    def __init__(self, collection):
        self.cards = collection.cards
        self.records = collection.catalog()[0]
        self.groups = {}
        for printing, record in self.records.items():
            self.groups.setdefault(deck_identity(record), []).append(printing)

    def get(self, key):
        ids = self.groups.get(key)
        if not ids:
            raise CardLookupError('Functional card is missing from the current cache.')
        records = [self.records[id] for id in sorted(ids)]
        # Stable selection; unknown evidence takes precedence over a false flag
        # when no printing establishes legality, so it cannot be called verified.
        record = next((r for r in records if r['card'].get('legal', {}).get('standard') is True and r.get('game') != 'pocket'), None)
        if record is None:
            record = next((r for r in records if 'standard' not in r['card'].get('legal', {})), records[0])
        record = deepcopy(self.cards.get(record['card']['id']))
        card = record['card']
        card['name'] = normalized_name(card['name'])
        if card.get('category') == 'Energy' and card.get('energyType') == 'Normal' and not key.startswith('deck-basic-energy:'):
            # Ambiguous upstream Normal is not an unlimited Basic Energy card.
            card['energyType'] = 'Special'
        return record


def blank():
    return dict(id=str(uuid4()), name='New Deck', format='standard', entries=[], has_saved=False, dirty=False)


def check_allocations(document):
    """Reject damaged documents rather than silently changing deck composition."""
    identities = set()
    for entry in document['entries']:
        if entry['identity'] in identities:
            raise ValueError('Duplicate functional deck entry; preserve this database.')
        identities.add(entry['identity'])
        allocations = entry['allocations']
        pairs = [(a['printing_id'], a['variant']) for a in allocations]
        if (not allocations or len(set(pairs)) != len(pairs)
            or any(type(a['quantity']) is not int or a['quantity'] <= 0 for a in allocations)
            or type(entry['quantity']) is not int
            or entry['quantity'] != sum(a['quantity'] for a in allocations)):
            raise ValueError('Deck allocations do not match the functional total; preserve this database.')


def migrate_document(document):
    for entry in document['entries']:
        entry['allocations'] = [dict(printing_id=entry.pop('printing_id'),
                                     variant=entry.pop('variant'), quantity=entry['quantity'])]
    check_allocations(document)
    return document


class Decks:
    def __init__(self, collection, path):
        self.collection = collection
        self.path = Path(path).resolve()
        if self.path in (collection.path, collection.cards.path):
            raise ValueError('Deck storage must be separate from cards and collection.')

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def initialize(self, db):
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1, 2):
            raise ValueError('Unsupported deck storage version. Preserve this database.')
        db.execute('CREATE TABLE IF NOT EXISTS workspace (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, document TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS saved_decks (id TEXT PRIMARY KEY, document TEXT NOT NULL, updated_at TEXT NOT NULL)')
        db.execute('INSERT OR IGNORE INTO workspace VALUES (1,0,?)', (json.dumps(blank()),))
        db.execute('CREATE TABLE IF NOT EXISTS default_printings (identity TEXT PRIMARY KEY, printing_id TEXT NOT NULL, variant TEXT NOT NULL)')
        if version == 1:
            # Called inside BEGIN IMMEDIATE. Archive every original document and
            # migrate active AND saved decks atomically; never infer old mixtures.
            db.execute('CREATE TABLE migration_v1_backup (kind TEXT, id TEXT, document TEXT NOT NULL, revision INTEGER, PRIMARY KEY(kind,id))')
            row = db.execute('SELECT * FROM workspace WHERE id=1').fetchone()
            db.execute('INSERT INTO migration_v1_backup VALUES (?,?,?,?)', ('workspace','1',row['document'],row['revision']))
            document = migrate_document(json.loads(row['document']))
            db.execute('UPDATE workspace SET document=?,revision=revision+1 WHERE id=1', (json.dumps(document),))
            for row in db.execute('SELECT * FROM saved_decks').fetchall():
                db.execute('INSERT INTO migration_v1_backup VALUES (?,?,?,NULL)', ('saved',row['id'],row['document']))
                document = migrate_document(json.loads(row['document']))
                db.execute('UPDATE saved_decks SET document=? WHERE id=?', (json.dumps(document),row['id']))
        db.execute('PRAGMA user_version=2')

    def validation(self, document):
        check_allocations(document)
        entries = document['entries']
        if not entries and not document['has_saved']:
            return dict(state='EMPTY', total=0, categories={}, reasons=[], unknown=[], limitations=[])
        # Inputs were bounded by DeckCommand and the mutation service. Construct
        # allows an empty/oversized draft to reach the authoritative rule service.
        deck = Deck.model_construct(name=document['name'], version='workspace', format='standard',
            cards=[DeckEntry.model_construct(card_id=e['identity'], count=e['quantity']) for e in entries], notes='')
        result = Lab(DeckProvider(self.collection), None).validate(deck, require_complete=document['has_saved'])
        total = result['total_cards']
        reasons = list(result['errors'])
        if document['has_saved'] and total < 60:
            reasons = [r for r in reasons if not r.startswith('Deck contains ')]
            reasons.insert(0, f'{60-total} cards remaining')
        state = 'INVALID' if reasons or result['unknown'] else 'VALID' if total == 60 else 'IN PROGRESS'
        return dict(state=state, total=total, categories=result['categories'], reasons=reasons,
                    unknown=result['unknown'], limitations=result['limitations'])

    def response(self, db, document, revision):
        snapshot = self.collection.snapshot()
        entries = []
        def available(printing_id, variant, key):
            record = snapshot.records.get(printing_id)
            return bool(record and deck_identity(record) == key and variant in snapshot.variants(printing_id))
        for stored in document['entries']:
            entry = deepcopy(stored)
            for allocation in entry['allocations']:
                ok = available(allocation['printing_id'], allocation['variant'], entry['identity'])
                allocation['available'] = ok
                allocation['owned'] = snapshot.ownership(allocation['printing_id'],allocation['variant']) if ok else None
            # Inspection anchor only; exact composition is always allocations[].
            anchor = next((a for a in entry['allocations'] if a['available']), entry['allocations'][0])
            entry.update(printing_id=anchor['printing_id'], variant=anchor['variant'],
                         presentation_available=anchor['available'], owned=anchor['owned'])
            entries.append(entry)
        defaults = {r['identity']:dict(printing_id=r['printing_id'],variant=r['variant'],
                    available=available(r['printing_id'],r['variant'],r['identity'])) for r in db.execute('SELECT * FROM default_printings')}
        return dict(schema_version=2, runtime_revision=os.getenv('POKELAB_BUILD_REVISION','development'), revision=revision,
                    defaults=defaults, deck={**document, 'entries':entries}, validation=self.validation(document),
                    saved=[dict(id=r['id'], name=json.loads(r['document'])['name'], updated_at=r['updated_at'])
                           for r in db.execute('SELECT * FROM saved_decks ORDER BY updated_at DESC,id')])

    def read(self):
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE'); self.initialize(db)
            row = db.execute('SELECT * FROM workspace WHERE id=1').fetchone()
            return self.response(db, json.loads(row['document']), row['revision'])

    def apply(self, command):
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE'); self.initialize(db)
            row = db.execute('SELECT * FROM workspace WHERE id=1').fetchone()
            if row['revision'] != command.revision:
                raise DeckConflict('Deck changed in another window. Reload the active deck before retrying.')
            document = json.loads(row['document'])
            check_allocations(document)
            action = command.action
            if action in ('new', 'open'):
                if document['dirty'] and not command.discard:
                    raise DeckConflict('Save changes or confirm discarding them before New/Open.')
                if action == 'new': document = blank()
                else:
                    saved = db.execute('SELECT document FROM saved_decks WHERE id=?', (command.deck_id,)).fetchone()
                    if saved is None: raise ValueError('Saved deck not found.')
                    document = json.loads(saved[0])
                    check_allocations(document)
            elif action == 'save':
                document['has_saved'] = True; document['dirty'] = False
                db.execute('INSERT INTO saved_decks VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET document=excluded.document,updated_at=excluded.updated_at',
                           (document['id'], json.dumps(document), datetime.now(timezone.utc).isoformat()))
            elif action == 'rename':
                if not command.name or not command.name.strip(): raise ValueError('A deck name is required.')
                document['name'] = command.name.strip(); document['dirty'] = True
            elif action == 'remove':
                if not command.identity: raise ValueError('Functional identity is required.')
                document['entries'] = [e for e in document['entries'] if e['identity'] != command.identity]
                document['dirty'] = True
            else:
                snapshot = self.collection.snapshot()
                if command.printing_id not in snapshot.records: raise ValueError('Printing is unavailable in the current cache.')
                record = snapshot.records[command.printing_id]
                key = deck_identity(record)
                if command.identity and command.identity != key: raise ValueError('Printing must have the same functional identity.')
                variant = command.variant or snapshot.default_variant(command.printing_id)
                snapshot.validate_variant(command.printing_id, variant)
                entry = next((e for e in document['entries'] if e['identity'] == key), None)
                if action == 'default_printing':
                    db.execute('INSERT INTO default_printings VALUES (?,?,?) ON CONFLICT(identity) DO UPDATE SET printing_id=excluded.printing_id,variant=excluded.variant',
                               (key, command.printing_id, variant))
                else:
                    if command.delta not in (-1, 1): raise ValueError('Quantity change must be -1 or +1.')
                    printing_id = command.printing_id
                    if not command.exact:
                        preferred = db.execute('SELECT * FROM default_printings WHERE identity=?', (key,)).fetchone()
                        if preferred and preferred['printing_id'] in snapshot.records:
                            preferred_record = snapshot.records[preferred['printing_id']]
                            if deck_identity(preferred_record) == key and preferred['variant'] in snapshot.variants(preferred['printing_id']):
                                printing_id, variant = preferred['printing_id'], preferred['variant']
                    if entry is None and command.delta == 1:
                        if len(document['entries']) >= 100: raise ValueError('Draft supports at most 100 functional entries.')
                        entry = dict(identity=key, quantity=0, allocations=[],
                                     name=record['card']['name'], category=record['card']['category'])
                        document['entries'].append(entry)
                    if entry:
                        allocation = next((a for a in entry['allocations'] if (a['printing_id'],a['variant']) == (printing_id,variant)),None)
                        if not command.exact and command.delta == -1 and allocation is None:
                            allocation = entry['allocations'][-1]  # Last allocated remaining variation.
                        if allocation is None and command.delta == 1:
                            allocation = dict(printing_id=printing_id,variant=variant,quantity=0)
                            entry['allocations'].append(allocation)
                        if allocation:
                            allocation['quantity'] = max(0, allocation['quantity'] + command.delta)
                        entry['allocations'] = [a for a in entry['allocations'] if a['quantity'] > 0]
                        entry['quantity'] = sum(a['quantity'] for a in entry['allocations'])
                        if entry['quantity'] > 999: raise ValueError('Draft quantity limit is 999.')
                        document['entries'] = [e for e in document['entries'] if e['quantity'] > 0]
                    document['dirty'] = True
            check_allocations(document)
            revision = row['revision'] + 1
            db.execute('UPDATE workspace SET revision=?,document=? WHERE id=1', (revision, json.dumps(document)))
            return self.response(db, document, revision)
