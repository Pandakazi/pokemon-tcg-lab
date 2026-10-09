"""Ingestion-time gameplay mapping. Legacy ownership/allocation identities stay intact."""
import hashlib
import json
import re
from .engine import functional_signature, normalized_name
from .library_identity import library_signature
from .standard_format import VERSION as FORMAT_VERSION, printing_legal

VERSION='gameplay-index-v1:'+FORMAT_VERSION


def gameplay_signature(card):
    basic=library_signature(card)
    if basic.startswith('library-basic-energy:'):return basic.replace('library-','deck-',1)
    value=json.loads(functional_signature(card,normalize_formatting=True))
    # Rarity is presentation except when it encodes an actual construction rule.
    rarity=card.get('rarity','').upper()
    if 'ACE SPEC' in rarity:value['construction_class']='ACE SPEC'
    if 'RADIANT' in rarity:value['construction_class']='RADIANT'
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def canonical_rank(card):
    set_id=card.get('set',{}).get('id','').casefold()
    rarity=card.get('rarity','').casefold()
    promo=bool('promo' in rarity or 'promo' in card.get('set',{}).get('name','').casefold() or re.match(r'^(?:svp|swshp|smp|xyp|bwp|dpp|hgp|mep)$',set_id))
    premium=bool(re.search(r'full art|illustration|secret|hyper|rainbow|shiny|special art|ultra rare|rare ultra|gold',rarity))
    number=str(card.get('localId',''))
    match=re.fullmatch(r'\d+',number)
    official=card.get('set',{}).get('cardCount',{}).get('official')
    if match and isinstance(official,int) and int(number)>official:premium=True
    return (promo,premium,int(number) if match else 1000000,number,card['id'])


def initialize(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS gameplay_functions (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, signature TEXT NOT NULL,
        standard INTEGER, canonical_printing TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS gameplay_name ON gameplay_functions(name);
      CREATE TABLE IF NOT EXISTS gameplay_printings (
        printing_id TEXT PRIMARY KEY, functional_id TEXT NOT NULL,
        standard INTEGER, rank TEXT NOT NULL, legacy_id TEXT NOT NULL, library_id TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS gameplay_members ON gameplay_printings(functional_id);
    ''')
    row=db.execute("SELECT value FROM metadata WHERE key='gameplay_index_version'").fetchone()
    if not row or json.loads(row[0])!=VERSION:rebuild(db)


def refresh_group(db,key):
    members=list(db.execute('SELECT printing_id,standard,rank FROM gameplay_printings WHERE functional_id=?',(key,)))
    if not members:
        db.execute('DELETE FROM gameplay_functions WHERE id=?',(key,));return
    legal=[r for r in members if r['standard']==1]
    value=1 if legal else None if any(r['standard'] is None for r in members) else 0
    selected=min(legal or members,key=lambda r:tuple(json.loads(r['rank'])))
    db.execute('UPDATE gameplay_functions SET standard=?,canonical_printing=? WHERE id=?',(value,selected['printing_id'],key))


def index_card(db,card,game, *, refresh=True):
    signature=gameplay_signature(card)
    key=signature if signature.startswith('deck-basic-energy:') else 'gameplay:'+hashlib.sha256(signature.encode()).hexdigest()[:32]
    old=db.execute('SELECT functional_id FROM gameplay_printings WHERE printing_id=?',(card['id'],)).fetchone()
    standard=printing_legal(card,game,basic=key.startswith('deck-basic-energy:'))
    db.execute('INSERT OR IGNORE INTO gameplay_functions VALUES (?,?,?,?,?)',(key,normalized_name(card['name']),signature,standard,card['id']))
    db.execute('INSERT OR REPLACE INTO gameplay_printings VALUES (?,?,?,?,?,?)',(card['id'],key,standard,json.dumps(canonical_rank(card)),hashlib.sha256(functional_signature(card).encode()).hexdigest()[:32],hashlib.sha256(library_signature(card).encode()).hexdigest()[:32]))
    if refresh:
        for affected in {key,old[0] if old else key}:refresh_group(db,affected)


def rebuild(db):
    # Only derived index rows are replaced, inside the caller's transaction.
    db.execute('DELETE FROM gameplay_printings');db.execute('DELETE FROM gameplay_functions')
    for row in db.execute('SELECT raw,game FROM cards').fetchall():index_card(db,json.loads(row['raw']),row['game'],refresh=False)
    for row in db.execute('SELECT id FROM gameplay_functions').fetchall():refresh_group(db,row[0])
    db.execute("INSERT OR REPLACE INTO metadata VALUES ('gameplay_index_version',?)",(json.dumps(VERSION),))


def require_current(db):
    row=db.execute("SELECT value FROM metadata WHERE key='gameplay_index_version'").fetchone()
    if not row or json.loads(row[0])!=VERSION:
        raise ValueError('Gameplay index requires an offline rebuild before deck resolution.')


def main():
    import argparse
    from contextlib import closing
    from tcg_lab.card_db import SQLiteCards
    parser=argparse.ArgumentParser(description='Rebuild derived gameplay/Standard index locally; no network or player-state writes.')
    parser.add_argument('--db',required=True)
    args=parser.parse_args();cards=SQLiteCards(args.db)
    with closing(cards.connect()) as db,db:rebuild(db)
    print('Gameplay index rebuilt; exact printing and player state preserved.')


if __name__=='__main__':main()
