"""Read-only, legal-first generation candidates; no workspace or provider writes."""
import json
import re
import sqlite3
from dataclasses import replace
from collections import Counter
from pathlib import Path
from .functional_index import require_current
from .standard_format import VERSION as FORMAT_VERSION
from .engine import normalized_name
from .mechanics_discovery import components, represent, load_taxonomy
from .alternative_retrieval import RetrievalIndex
from .rules.models import digest

MAX_CANDIDATES = 48
MAX_BYTES = 14000
MAX_REPAIR_SLOTS = 8
ROLES = ('trainer cards draw', 'trainer cards search Pokémon', 'trainer cards search supporter',
         'trainer cards evolution acceleration', 'trainer cards recover Pokémon from discard',
         'trainer cards gust', 'trainer cards switch your Active Pokémon', 'trainer cards stadium',
         'trainer cards energy recovery', 'trainer cards energy acceleration',
         'trainer cards hand disruption', 'item lock', 'damage counters', 'basic Pokémon draw', 'heal')
FIELDS = ('name','category','stage','evolveFrom','types','hp','suffix',
          'attacks','abilities','effect','trainerType','energyType','rarity','rules')


def legal_pool(path):
    """One row per indexed legal gameplay identity, never raw legality flags."""
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True) as db:
        db.row_factory=sqlite3.Row
        db.execute('BEGIN')
        require_current(db)
        return [dict(functional_id=r['id'],printing_id=r['canonical_printing'],
                     card=json.loads(r['raw']),checked_at=r['checked_at']) for r in db.execute(
            'SELECT f.id,f.canonical_printing,c.raw,c.checked_at FROM gameplay_functions f '
            'JOIN cards c ON c.id=f.canonical_printing WHERE f.standard=1 ORDER BY f.id')]


def retrieval(pool):
    """Reuse Pass 2 ranking/representation on the eligible universe only."""
    cards=[];effects=[];taxonomy=load_taxonomy()
    for row in pool:
        raw=row['card'];key=row['functional_id']
        cards.append(dict(printing=raw['id'],name=raw['name'],category=raw['category'],
            functional_identity=key,standard=True,source_fields={k:raw[k] for k in FIELDS if k in raw}))
        effects.extend(replace(represent(raw,kind,i,item,row['checked_at'],taxonomy),
            functional_identity=key) for kind,i,item in components(raw))
    return RetrievalIndex(cards,effects,digest(cards))


def build(path, question, preferred_printings=()):
    pool=legal_pool(path);by_id={r['functional_id']:r for r in pool}
    index=retrieval(pool);selected={};missing=[];budget=[]
    by_name={}
    for row in pool:by_name.setdefault(normalized_name(row['card']['name']),[]).append(row)
    q=normalized_name(question)
    def add(row, role, seen=None):
        key=row['functional_id']
        if key in selected:return
        seen=set() if seen is None else seen
        if key in seen:return
        seen.add(key)
        raw=row['card'];parent=raw.get('evolveFrom')
        if parent:
            parents=by_name.get(normalized_name(parent),[])
            if not parents:missing.append('legal-evolution-predecessor:'+parent)
            for ancestor in parents[:2]:add(ancestor,'evolution-family',seen)
        value=dict(functional_id=key,printing_id=row['printing_id'],role=role,
            **{k:raw[k] for k in FIELDS if k in raw})
        if len(selected)>=MAX_CANDIDATES or len(json.dumps([*selected.values(),value],ensure_ascii=False).encode())>MAX_BYTES:
            budget.append(key);return
        selected[key]=value
    core=[r for r in pool if re.search(r'(?<!\w)'+re.escape(normalized_name(r['card']['name']))+r'(?!\w)',q)]
    for row in sorted(core,key=lambda r:(-len(r['card']['name']),r['functional_id'])):add(row,'requested-core')
    for row in pool:
        if row['printing_id'] in preferred_printings:add(row,'existing-concept')
    # Basic Energy and ancestors must not lose all slots to ranked support text.
    for row in pool:
        if row['functional_id'].startswith('deck-basic-energy:'):add(row,'basic-energy')
    groups=[index.search(text[:1000],limit=4)['results'] for text in (question,*ROLES)]
    for rank in range(4):
        for role,hits in zip(('requested-mechanics',*ROLES),groups):
            if rank<len(hits):add(by_id[hits[rank]['functional_identity']],role)
    # Supplemental attackers/utility/uncategorized text; no strategic ranking claimed.
    core_types={t for r in core for t in r['card'].get('types',[])}
    rest=sorted(pool,key=lambda r:(not bool(core_types.intersection(r['card'].get('types',[]))),r['functional_id']))
    for row in rest:add(row,'additional-legal-option')
    return dict(version='pokelab-standard-sandbox-v1',format=FORMAT_VERSION,
        legal_universe_count=len(pool),candidates=list(selected.values()),
        limitations=['Local indexed coverage only; legality is not a guarantee of a viable engine.']+sorted(set(missing))+(['bounded-candidate-subset;no-iterative-expansion'] if budget else []),
        instruction='Choose only these functional candidates for generated_deck. Use exact names and quantities; printing_id may disambiguate genuinely different same-name cards. Preserve the requested core. Exactly 60 cards; printed effects are not tournament evidence. If options are insufficient, explain the local cache/candidate limitation; never invent outside cards.')


def small_repair(report):
    if not report:return False
    counts=Counter()
    for row in report['cards']:
        if not row['card_id'].startswith('deck-basic-energy:'):
            counts[normalized_name(row['canonical_name'])]+=row['quantity']
    if sum(max(0,n-4) for n in counts.values())>MAX_REPAIR_SLOTS:return False
    return (abs(60-report['total_cards'])<=MAX_REPAIR_SLOTS
        and sum(r['quantity'] for r in report['unresolved'])<=MAX_REPAIR_SLOTS
        and len(report['hard_validation'])<=4)


def repair_distance(requirements, report):
    before={r['printing_id']:r['quantity'] for r in requirements.get('cards',[])}
    after={r['printing_id']:r['quantity'] for r in report['cards']}
    return max(sum(max(0,before.get(k,0)-after.get(k,0)) for k in before),
               sum(max(0,after.get(k,0)-before.get(k,0)) for k in after))
