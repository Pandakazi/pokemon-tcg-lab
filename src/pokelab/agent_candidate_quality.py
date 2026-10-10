"""Small, inspectable generation prior over existing cached evidence and mechanics."""
from collections import Counter,defaultdict
from datetime import date,timedelta
from pathlib import Path
import re
import sqlite3
from .api import ReadOnlyCards
from .competitive import Competitive
from .engine import normalized_name
from .agent_context_sources import stamp
from .alternative_retrieval import INTENTS

ROLES=('setup-search','draw-consistency','evolution-support','recovery','gust',
       'disruption','mobility','stadium','tool','energy-support','utility','secondary-attacker')


def prior(cards_path,competitive_path,pool,core,question,format_start=None,today=None):
    """Reuse main-Limitless normalized cache; never ingest, remap, or write."""
    empty=({}, {},dict(status='unavailable',source='limitless-main'))
    if not competitive_path:return empty
    today=today or date.today()
    try:
        before=stamp(Path(competitive_path))
        events,decks,_=Competitive(ReadOnlyCards(cards_path),competitive_path,format_start).evidence()
        with sqlite3.connect(Path(cards_path).resolve().as_uri()+'?mode=ro',uri=True) as db:
            aliases=defaultdict(set)
            for old,new in db.execute('SELECT legacy_id,functional_id FROM gameplay_printings'):aliases[old].add(new)
        legal={r['functional_id'] for r in pool}
        dates={e['id']:date.fromisoformat(e['date']) for e in events if date.fromisoformat(e['date'])<=today and (not format_start or e['date']>=format_start)}
        rows=[]
        for d in decks:
            if not d['resolved'] or d['event_id'] not in dates:continue
            vector=Counter()
            for old,n in d['cards'].items():
                keys=aliases.get(old,{old} if old in legal else set())
                if len(keys)==1:vector[next(iter(keys))]+=n
            rows.append(dict(deck=d,vector=vector,date=dates[d['event_id']]))
        if not rows:return empty
        core_ids={r['functional_id'] for r in core if r['card']['category']=='Pokemon'}
        q=normalized_name(question)
        named=[r for r in rows if r['deck']['raw'].get('archetype_name') and normalized_name(r['deck']['raw']['archetype_name']) in q]
        matching=named or [r for r in rows if core_ids.intersection(r['vector'])]
        # Prefer recent evidence; pick the strongest weighted classified shell.
        anchor=max((r['date'] for r in matching),default=max(r['date'] for r in rows))
        weights=Counter()
        for r in matching:
            if r['date']>=anchor-timedelta(days=89):weights[r['deck']['raw']['archetype_id']]+=2**(-(anchor-r['date']).days/30)
        archetype=min(weights,key=lambda k:(-weights[k],k)) if weights else None
        relevant=[r for r in rows if r['deck']['raw'].get('archetype_id')==archetype and anchor-timedelta(days=89)<=r['date']<=anchor] if archetype else []
        field_anchor=max(r['date'] for r in rows)
        field=[r for r in rows if field_anchor-timedelta(days=89)<=r['date']<=field_anchor]
        def usage(sample,latest):
            totals=Counter();denominator=0
            for r in sample:
                w=2**(-(latest-r['date']).days/30);denominator+=w
                for key in r['vector']:
                    if key in legal:totals[key]+=w
            return {key:value/denominator for key,value in totals.items()} if denominator else {}
        if stamp(Path(competitive_path))!=before:return empty
        return usage(relevant,anchor),usage(field,field_anchor),dict(status='observed' if relevant else 'generic-field-only',
            source='limitless-main',archetype=archetype,eligible_lists=len(relevant),limited_evidence=len(relevant)<15,
            latest_event=max((r['date'] for r in relevant),default=anchor).isoformat(),age_days=(today-max((r['date'] for r in relevant),default=anchor)).days,lookback_days=90,half_life_days=30,
            weighting='cached-event-relative exponential inclusion; ranking prior, not prevalence or optimal counts',
            event_ids=sorted({r['deck']['event_id'] for r in relevant})[:12])
    except (OSError,sqlite3.Error,ValueError,KeyError,TypeError):return empty


def energy_types(rows):
    result=set()
    for row in rows:
        raw=row['card']
        result.update(t for attack in raw.get('attacks',[]) for t in attack.get('cost',[]) if t!='Colorless')
        if row['functional_id'].startswith('deck-basic-energy:'):result.add(row['functional_id'].split(':',1)[1])
    return result


def rank(pool,index,core,usage,field):
    core_ids={r['functional_id'] for r in core}
    types={t for r in core for t in r['card'].get('types',[])}
    evolving=any(r['card'].get('evolveFrom') for r in core)
    core_mechanics={m for r in core for e in index.by_identity[r['functional_id']] for m in e.mechanics}
    result={}
    for row in pool:
        key=row['functional_id'];raw=row['card'];effects=index.by_identity[key]
        texts=[e.normalized_text for e in effects]
        mechanics={i.concept for i in INTENTS if any(re.search(i.evidence,t) for t in texts)}
        roles=set()
        if 'pokemon_search' in mechanics:roles.add('setup-search')
        if 'draw' in mechanics or any('look at' in t and 'hand' in t for t in texts):roles.add('draw-consistency')
        if 'evolution_acceleration' in mechanics or any(re.search(r'\bevolve|evolution pokémon|stage 2',t) for t in texts):roles.add('evolution-support')
        if mechanics & {'pokemon_recovery','energy_recovery'}:roles.add('recovery')
        if 'gust' in mechanics:roles.add('gust')
        if mechanics & {'hand_disruption','item_lock','ability_lock','energy_denial'}:roles.add('disruption')
        if any(re.search(r'switch.*your|retreat cost.*less|no retreat cost',t) for t in texts):roles.add('mobility')
        if raw.get('trainerType')=='Stadium':roles.add('stadium')
        if raw.get('trainerType')=='Tool':roles.add('tool')
        if mechanics & {'energy_acceleration','energy_recovery'}:roles.add('energy-support')
        if raw['category']=='Pokemon' and (raw.get('abilities') or 'item_lock' in mechanics):roles.add('utility')
        if raw['category']=='Pokemon' and raw.get('attacks') and (not types or types.intersection(raw.get('types',[]))):roles.add('secondary-attacker')
        direct=bool(roles & {'setup-search','draw-consistency','recovery','energy-support'}) or evolving and 'evolution-support' in roles
        # Reuse represented mechanics so singular/plural printed forms share the
        # same bounded concept; generic damage/draw alone is not engine synergy.
        represented={m for e in effects for m in e.mechanics}
        synergy=bool(core_mechanics.intersection(represented)-{'draw','printed_damage','inspect','top_deck_inspection'})
        burden=0 if key in core_ids else 24 if raw.get('stage')=='Stage2' else 16 if raw.get('evolveFrom') else 0
        mismatch=8 if raw['category']=='Pokemon' and types and raw.get('attacks') and not types.intersection(raw.get('types',[])) else 0
        score=round(100*usage.get(key,0)+15*field.get(key,0)+18*direct+6*bool(roles & {'gust','disruption','mobility'})+8*synergy-burden-mismatch,3)
        result[key]=dict(score=score,roles=sorted(roles),recent_prior=round(usage.get(key,0),4),
            core_amplification=direct,setup_burden=burden,type_mismatch=mismatch,mechanical_synergy=synergy)
    return result
