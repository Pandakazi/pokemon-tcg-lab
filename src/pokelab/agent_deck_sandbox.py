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


def build(path, question, preferred_printings=(), *, competitive_path=None,format_start=None,today=None,selected_core=None):
    pool=legal_pool(path);by_id={r['functional_id']:r for r in pool}
    index=retrieval(pool);selected={};missing=[];budget=[]
    by_name={}
    for row in pool:by_name.setdefault(normalized_name(row['card']['name']),[]).append(row)
    q=normalized_name(question)
    from .agent_candidate_quality import prior,rank,energy_types,ROLES as QUALITY_ROLES
    from .agent_consensus import baseline
    consensus=baseline(path,competitive_path,pool,question,format_start,today)
    from .agent_build_core import resolve
    core,core_resolution=resolve(pool,question,consensus,selected_core)
    core_ids={r['functional_id'] for r in core}
    usage,field,provenance=prior(path,competitive_path,pool,core,question,format_start,today)
    family={r['functional_id']:r for r in core}
    pending=list(core)
    while pending:
        child=pending.pop()
        for parent in by_name.get(normalized_name(child['card'].get('evolveFrom','')),[]):
            if parent['functional_id'] not in family:
                family[parent['functional_id']]=parent;pending.append(parent)
    quality=rank(pool,index,list(family.values()),usage,field)
    consensus_ids={r['candidate_id'] for r in consensus['cards']} if consensus and consensus['status']=='available' else set()
    order=lambda r:(-quality[r['functional_id']]['score'],normalized_name(r['card']['name']),r['functional_id'])
    def add(row, role, seen=None, ancestors=True):
        key=row['functional_id']
        if key in selected:return
        seen=set() if seen is None else seen
        if key in seen:return
        seen.add(key)
        raw=row['card'];parent=raw.get('evolveFrom')
        if parent and ancestors:
            parents=by_name.get(normalized_name(parent),[])
            if not parents:missing.append('legal-evolution-predecessor:'+parent)
            for ancestor in sorted(parents,key=order)[:2]:add(ancestor,'evolution-family',seen)
        value=dict(candidate_id=key,printing_id=row['printing_id'],role=role,
            ace_spec='ACE SPEC' in raw.get('rarity','').upper(),
            basic_energy=key.startswith('deck-basic-energy:'),copy_limit_name=normalized_name(raw['name']),
            requested_core=key in core_ids,
            predecessor_candidate_ids=[r['functional_id'] for r in by_name.get(normalized_name(parent),[]) if r['functional_id'] in selected or r['functional_id'] in consensus_ids] if parent else [],
            **{k:raw[k] for k in FIELDS if k in raw})
        # Consensus quantities already establish these slots; per-card ranking
        # annotations are redundant and must not crowd a complete baseline out.
        if core and role!='consensus':value['ranking']={k:quality[key][k] for k in ('score','recent_prior')}
        if len(selected)>=MAX_CANDIDATES or len(json.dumps([*selected.values(),value],ensure_ascii=False).encode())>MAX_BYTES:
            budget.append(key);return
        selected[key]=value
    if consensus and consensus['constrained']:
        for row in sorted(core,key=lambda r:(-len(r['card']['name']),r['functional_id'])):add(row,'requested-core')
    if consensus and consensus['status']=='available':
        for item in consensus['cards']:add(by_id[item['candidate_id']],'consensus',ancestors=False)
        # Model candidate admission cannot invalidate a complete local baseline.
        # Direct generation validates its identities separately; exploration stays bounded.
    for row in sorted(core,key=lambda r:(-len(r['card']['name']),r['functional_id'])):add(row,'requested-core')
    for row in pool:
        if row['printing_id'] in preferred_printings:add(row,'existing-concept')
    # Only plausible Energy: printed core costs, requested types, or recent shell.
    energy=energy_types(core)
    energy.update(energy_types([r for r in pool if usage.get(r['functional_id'],0)>=.25]))
    for row in pool:
        if row['functional_id'].startswith('deck-basic-energy:') and normalized_name(row['functional_id'].split(':',1)[1]) in q:energy.update(energy_types([row]))
    if not core:energy.update(energy_types(pool))  # no type constraint was established
    for row in pool:
        if row['functional_id'].startswith('deck-basic-energy:') and row['functional_id'].split(':',1)[1] in energy:add(row,'basic-energy')
    if not core:
        # Without a named core, preserve the generic discovery fallback instead
        # of pretending that a specific engine/archetype has been established.
        hits=[index.search(text[:1000],limit=4)['results'] for text in (question,*ROLES)]
        for depth in range(4):
            for role,rows in zip(('requested-mechanics',*ROLES),hits):
                if depth<len(rows):add(by_id[rows[depth]['functional_identity']],role)
        for row in pool:add(row,'additional-legal-option')
    ranked=sorted((r for r in pool if core and not r['functional_id'].startswith('deck-basic-energy:')),key=order)
    # One slot per available role first, then a second pass. Multi-role cards share space.
    groups={role:[r for r in ranked if role in quality[r['functional_id']]['roles']] for role in QUALITY_ROLES}
    for role,rows in groups.items():
        if any(role in quality[key]['roles'] for key in selected if key not in family):continue
        choices=[r for r in rows if r['functional_id'] not in selected]
        if choices:add(choices[0],role)
    # Bounded creativity cannot displace the first infrastructure pass.
    creative=[r for r in ranked if r['functional_id'] not in selected and not usage.get(r['functional_id']) and quality[r['functional_id']]['mechanical_synergy']]
    # One compact wildcard leaves the bulk of remaining bytes for recent staples.
    for row in creative:
        if len(json.dumps(row['card'],ensure_ascii=False).encode())<=800:
            add(row,'creative');break
    # Fill remaining capacity by the explicit prior; avoid giving weak second role
    # options precedence over missing staples from other roles.
    for row in ranked:
        if usage.get(row['functional_id'],0)>0 or quality[row['functional_id']]['score']>0 or not core:add(row,'recent-archetype' if usage.get(row['functional_id'],0) else 'support-option')
    # Relevant secondary attackers may require an additional Basic Energy type.
    extra_energy=energy_types([by_id[key] for key,value in selected.items() if value['role']=='secondary-attacker' and quality[key]['score']>0])
    for row in pool:
        if row['functional_id'].startswith('deck-basic-energy:') and row['functional_id'].split(':',1)[1] in extra_energy:add(row,'basic-energy')
    for value in selected.values():
        value['predecessor_candidate_ids']=[key for key in value['predecessor_candidate_ids'] if key in selected]
    return dict(version='pokelab-standard-sandbox-v2',format=FORMAT_VERSION,
        legal_universe_count=len(pool),candidates=list(selected.values()),competitive_prior=provenance,consensus=consensus,core_resolution=core_resolution,
        limitations=['Local indexed coverage only; legality is not a guarantee of a viable engine.']+sorted(set(missing))+(['bounded-candidate-subset;no-iterative-expansion'] if budget else []),
        instruction='Use recent-archetype priors and core support as the default foundation, allowing reasoned deviations. Ranking is a heuristic, not a tournament ranking or recommended copy count; recent_prior is recency-weighted cached inclusion, not population prevalence. Choose only supplied candidate_id values for generated_deck entries, with exact positive integer quantities. Do not reselect ambiguous cards by bare name. Names are optional but must match the selected candidate; printing is backend-derived. Total quantity must equal 60. Sum of quantities with ace_spec=true must be <=1. Group by copy_limit_name for the ordinary maximum of 4, except basic_energy=true. Preserve requested_core candidates and consider predecessor_candidate_ids for evolution lines. Printed effects are not tournament evidence. If options are insufficient, explain the local cache/candidate limitation; never invent outside cards.')


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
    added={k:max(0,n-before.get(k,0)) for k,n in after.items()}
    # Choosing an identity for an already proposed unresolved name fills that slot;
    # it is not another missing slot. Replacements of different names still count.
    for slot in requirements.get('unresolved',[]):
        remaining=slot['quantity']
        for row in report['cards']:
            if normalized_name(slot.get('name',''))!=normalized_name(row['canonical_name']):continue
            if slot.get('candidate_id') and slot['candidate_id']!=row.get('candidate_id'):continue
            credit=min(remaining,added[row['printing_id']])
            added[row['printing_id']]-=credit;remaining-=credit
    return max(sum(max(0,n-after.get(k,0)) for k,n in before.items()),sum(added.values()))


def candidate_key(row):
    """Accept an existing in-memory v1 sandbox while new packets use candidate_id."""
    return row.get('candidate_id',row.get('functional_id'))


def accounting(report):
    resolved=report['total_cards']
    unresolved=sum(r['quantity'] for r in report['unresolved'])
    proposed=resolved+unresolved
    return dict(resolved_count=resolved,unresolved_proposed_count=unresolved,
        proposed_total=proposed,true_missing_count=max(0,60-proposed),
        excess_proposed_count=max(0,proposed-60))


def construction_violations(rows):
    counts=Counter();ace=0
    for row in rows:
        raw=row.get('printed',{})
        if 'ACE SPEC' in raw.get('rarity','').upper():ace+=row['quantity']
        if not row['card_id'].startswith('deck-basic-energy:'):
            counts[normalized_name(row['canonical_name'])]+=row['quantity']
    result=[dict(kind='name_copy_limit',name=name,count=n,maximum=4,excess=n-4)
            for name,n in sorted(counts.items()) if n>4]
    if ace>1:result.append(dict(kind='ace_spec',count=ace,maximum=1,excess=ace-1))
    return result
