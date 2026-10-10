"""Read-only, source-labeled recent-variant consensus. No clustering or writes."""
from collections import Counter,defaultdict
from datetime import date
from fractions import Fraction
from math import ceil
from pathlib import Path
import re
import sqlite3
from .api import ReadOnlyCards
from .competitive import Competitive
from .engine import normalized_name
from .agent_context_sources import stamp


def build_request(question):
    if re.search(r'\b(?:those|these|the proposed) changes\b',question,re.I):return False
    return bool(re.search(r'^(?:(?:please|can you|could you|would you)\s+)*(?:(?:build|create)\b|make\b.*\b(?:deck|list)\b)',question,re.I))


def words(text):return tuple(w for w in re.findall(r'\w+',text.casefold()) if w!='ex')


# Presentation requirements are not strategic permission to change the deck.
PRESENTATION_WORDS=set('build rebuild create make me a an the deck list standard legal complete card cards 60 please can could would you competitive current recent for with and put it in form every slot exact include category subtotals sure total is exactly return show all quantities counts count print format formatted as table of another'.split())


def custom_request(question,label=''):
    style=bool(re.search(r'\b(?:aggressive|control|experimental|custom|weird|budget|mill|stall|toolbox)\b',question,re.I))
    clauses=re.findall(r'\b(?:with|around|using|include|featuring|plus|without|except|avoid|exclude|only)\b([^.!?]*)',question,re.I)
    return style or any(set(words(clause))-set(words(label))-PRESENTATION_WORDS for clause in clauses)


def select(rows,question):
    """Two newest relevant events; depth first, then one older event at a time."""
    labels={r['variant']:r['label'] for r in rows if r['variant']!='unknown'}
    q=set(words(question))
    matches=[k for k,v in labels.items() if set(words(v))<=q]
    if not matches:return None
    base=min(matches,key=lambda k:(len(words(labels[k])),k))
    chosen=max(matches,key=lambda k:(len(words(labels[k])),k))
    explicit=len(words(labels[chosen]))>len(words(labels[base]))
    family={k for k,v in labels.items() if words(v)[:len(words(labels[base]))]==words(labels[base])}
    relevant=[r for r in rows if r['variant'] in ({chosen} if explicit else family)]
    events=sorted({(r['date'],r['event']) for r in relevant},reverse=True)
    for count in range(min(2,len(events)),len(events)+1):
        ids={e for _,e in events[:count]};pool=[r for r in relevant if r['event'] in ids]
        totals=Counter(r['variant'] for r in pool)
        variant=chosen if explicit else min(totals,key=lambda k:(-totals[k],k))
        cohort=[r for r in pool if r['variant']==variant]
        deepest=max(r['placement'] for r in cohort)
        for band in sorted(set([8,16,32,max(32,deepest)])):
            sample=[r for r in cohort if r['placement']<=band]
            if len(sample)>=8:
                break
        if len(sample)>=8 or count==len(events):
            constrained=custom_request(question,labels[variant])
            return dict(sample=sample,event_ids=[e for _,e in events[:count]],variant=variant,label=labels[variant],
                placement_band=band,dominance=dict(totals),explicit_variant=explicit,constrained=constrained)
    return None


def weight(placement):return Fraction(5,4) if placement==1 else Fraction(23,20) if placement<=8 else Fraction(21,20) if placement<=16 else Fraction(1)


def shape_targets(expected,cards):
    totals={c:sum((n for k,n in expected.items() if cards[k]['category']==c),Fraction()) for c in ('Pokemon','Trainer','Energy')}
    target={c:int(n) for c,n in totals.items()}
    for c in sorted(totals,key=lambda c:(-(totals[c]-target[c]),c))[:60-sum(target.values())]:target[c]+=1
    return totals,target


def construct(expected,cards,universe):
    """Largest marginal expected-copy deficits with shape and path constraints."""
    _,targets=shape_targets(expected,cards);counts=Counter()
    by_name=defaultdict(list)
    for k,r in universe.items():by_name[normalized_name(r['name'])].append(k)
    candy=[k for k,r in cards.items() if normalized_name(r['name'])=='rare candy' and 'stage 2' in r.get('effect','').casefold()]
    def bundle(key,existing,seen=frozenset()):
        if key in seen:return None
        raw=cards[key];parent=raw.get('evolveFrom')
        if not parent or raw.get('stage')=='Basic':return Counter({key:1})
        parents=by_name[normalized_name(parent)]
        if any(existing[p]>0 for p in parents):return Counter({key:1})
        choices=[]
        for p in parents:
            if p in expected:
                path=bundle(p,existing,seen|{key})
                if path is not None:choices.append(path+Counter({key:1}))
        if raw.get('stage')=='Stage2':
            basics={b for p in parents for b in by_name[normalized_name(universe[p].get('evolveFrom',''))] if universe[b].get('stage')=='Basic' and b in expected}
            for b in basics:
                for c in candy:
                    choices.append(Counter({key:1})+Counter({b:1} if not existing[b] else {})+Counter({c:1} if not existing[c] else {}))
        return min(choices,key=lambda x:(sum(x.values()),-sum(expected[k] for k in x),tuple(sorted(x)))) if choices else None
    def fits(delta):
        after=counts+delta;names=Counter();categories=Counter();ace=0
        for k,n in after.items():
            if n>ceil(expected[k]):return False
            r=cards[k];categories[r['category']]+=n
            if not k.startswith('deck-basic-energy:'):names[normalized_name(r['name'])]+=n
            if 'ACE SPEC' in r.get('rarity','').upper():ace+=n
        return max(names.values(),default=0)<=4 and ace<=1 and all(categories[c]<=targets[c] for c in targets)
    while sum(counts.values())<60:
        choices=[]
        for k in sorted(expected):
            delta=bundle(k,counts)
            if delta is None or not fits(delta):continue
            # Highest remaining expected-copy strength; prerequisite costs count.
            score=sum((expected[x]-counts[x]-Fraction(n-1,2))*n for x,n in delta.items())/sum(delta.values())
            choices.append((score,k,delta))
        if not choices:return None
        _,_,delta=min(choices,key=lambda x:(-x[0],x[1]));counts.update(delta)
    return dict(counts)


def baseline(path,competitive_path,pool,question,format_start=None,today=None):
    if not competitive_path or not build_request(question):return None
    today=today or date.today();legal={r['functional_id']:r['card'] for r in pool}
    try:
        before=stamp(Path(competitive_path))
        events,decks,_=Competitive(ReadOnlyCards(path),competitive_path,format_start).evidence()
        dates={e['id']:e['date'] for e in events if e['date']<=today.isoformat() and (not format_start or e['date']>=format_start)}
        aliases=defaultdict(set)
        with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as db:
            for old,new in db.execute('SELECT legacy_id,functional_id FROM gameplay_printings'):aliases[old].add(new)
        rows=[]
        for d in decks:
            if not d['resolved'] or d['event_id'] not in dates:continue
            vector=Counter();valid=True
            for old,n in d['cards'].items():
                keys=aliases.get(old,{old} if old in legal else set())
                if len(keys)!=1 or next(iter(keys)) not in legal or type(n)!=int or n<=0:valid=False;break
                vector[next(iter(keys))]+=n
            if valid and sum(vector.values())==60:
                rows.append(dict(event=d['event_id'],date=dates[d['event_id']],placement=d['rank'],variant=d['raw']['archetype_id'],label=d['raw']['archetype_name'],cards=dict(vector)))
        selected=select(rows,question)
        if not selected:return None
        sample=selected.pop('sample');total=sum(weight(r['placement']) for r in sample)
        expected=defaultdict(Fraction)
        for r in sample:
            for k,n in r['cards'].items():expected[k]+=n*weight(r['placement'])/total
        cards={k:legal[k] for k in expected};shape,_=shape_targets(expected,cards)
        counts=construct(expected,cards,legal) if len(sample)>=8 else None
        if stamp(Path(competitive_path))!=before:return None
        return dict(version='pokelab-consensus-v1',status='available' if counts else 'insufficient_sample' if len(sample)<8 else 'allocation_unavailable',
            **selected,sample_size=len(sample),latest_event=max(r['date'] for r in sample),
            placement_weights={'winner':1.25,'top8':1.15,'top16':1.05,'deeper':1},
            shape={k:round(float(n),4) for k,n in shape.items()},
            cards=[dict(candidate_id=k,name=cards[k]['name'],quantity=n,expected_copies=round(float(expected[k]),4)) for k,n in sorted((counts or {}).items())],
            energy=[dict(candidate_id=k,name=cards[k]['name'],expected_copies=round(float(n),4)) for k,n in sorted(expected.items()) if cards[k]['category']=='Energy'],
            source='limitless-main',algorithm='shape-constrained-expected-copy-allocation-v1')
    except (OSError,sqlite3.Error,ValueError,KeyError,TypeError,ZeroDivisionError):return None


# Historical compatibility only; initial builds now use direct_generation and
# this contract is not sent to providers.
CONTRACT='''
candidate_sandbox.consensus is PokéLab's deterministic recent competitive consensus
for one Limitless-labeled variant. Its 60 slots and shape are the strong default,
not an instruction to invent a fresh archetype or use Energy as filler. For a generic
request, omit an action block to accept it and explain the plan naturally. If changing
it, return a full generated_deck with rationale: at most eight replaced copies,
with concrete reasons for Energy/core/search/staple changes. For constrained=true,
explicit user requirements take priority and may justify broader deviation. All
changes still require ordinary identity/legality/construction validation. This is
a derived baseline, not an observed winning list or a guarantee of competitive success.
'''


def proposal_for(consensus):
    from .agent_deck_proposals import Proposal
    return Proposal.model_validate(dict(kind='list',name=consensus['label']+' — recent consensus',
        cards=[dict(candidate_id=r['candidate_id'],quantity=r['quantity']) for r in consensus['cards']],
        rationale='Deterministic recent source-labeled variant consensus.'))


def permitted_deviation(proposal,consensus,candidates):
    """Legacy comparison helper, not authorization for initial-build changes."""
    if proposal is None or proposal.kind!='list':return False
    before={r['candidate_id']:r['quantity'] for r in consensus['cards']};after=Counter()
    raw={r['candidate_id']:r for r in candidates}
    for r in proposal.cards:
        if r.candidate_id not in raw:return False
        after[r.candidate_id]+=r.quantity
    if sum(after.values())!=60:return False
    difference=sum(max(0,n-before.get(k,0)) for k,n in after.items())
    if difference>8 or difference and not proposal.rationale.strip():return False
    # Bounded construction check, not a rules engine: a normal predecessor or
    # printed Rare Candy infrastructure must connect every evolved card.
    names={normalized_name(raw[k]['name']) for k in after}
    candy=any(normalized_name(raw[k]['name'])=='rare candy' and 'stage 2' in raw[k].get('effect','').casefold() for k in after)
    for k in after:
        r=raw[k];parent=r.get('evolveFrom')
        if not parent or normalized_name(parent) in names:continue
        basics={normalized_name(p.get('evolveFrom','')) for p in candidates if normalized_name(p['name'])==normalized_name(parent)}
        if not (r.get('stage')=='Stage2' and candy and names & basics):return False
    return True
