"""Read-only bounded projection of the accepted whole-Standard retrieval layer."""
from datetime import date
import json
import re
from typing import Literal

from pydantic import Field
from .agent_context_models import Frozen, Coverage, Reference
from .agent_context_sources import stamp, Unavailable
from .alternative_retrieval import RetrievalIndex, BY_CONCEPT, parse_query
from .deck_research import Item, fields
from .mechanics_discovery import normalize
from .rules.models import digest

CAP = 5
COMPONENT_CAP = 2
BYTES = 24576


class PoolPacket(Frozen):
    version: Literal['pokelab-card-pool-evidence-v1'] = 'pokelab-card-pool-evidence-v1'
    request: dict
    query: dict
    corpus_hash: str
    evidence: tuple[Item, ...]
    references: tuple[Reference, ...]
    coverage: Coverage


class PoolEnvelope(Frozen):
    version: Literal['pokelab-card-pool-research-v1'] = 'pokelab-card-pool-research-v1'
    packet: PoolPacket
    active_deck: dict
    omitted: tuple[str, ...] = ()
    boundary: str | None = None
    content_hash: str
    # Local guard lookup only; never serialized into provider context or reports.
    catalog_names: tuple[str, ...] = Field(default=(), exclude=True, repr=False)


def query_text(question, reference):
    """Integration aliases for canonical product wording; original question retained.

    This does not change accepted Pass 2 parsing/ranking or benchmark artifacts.
    Explicit existing mechanics take precedence over any contextual expansion.
    """
    q=normalize(question).replace('pokemon','pokémon')
    if parse_query(question[:1000])['concepts']: return question[:1000]
    if re.search(r'\bmilling\b|deck(?:ing)? (?:my |the )?opponent out',q): return 'mill my opponent'
    if re.search(r'moving damage counters',q): return 'move damage counters'
    if re.search(r'deny.*opponent.*energy',q): return 'energy denial'
    if reference and re.search(r'something like|similar|same role',q): return 'similar role'
    return question[:1000]


def build(request,sources,today=None):
    from .agent_research import ResearchUnavailable, canonical
    before=stamp(sources.paths['cards'])
    try:
        index=RetrievalIndex.from_database(sources.paths['cards'])
        active={};reference=None;reference_card=None;deck_ids=[]
        with sources.snapshot() as (dbs,errors):
            if 'cards' in errors: raise ResearchUnavailable('context_unavailable')
            if request.printing:
                reference_card=next((c for c in index.cards if c['printing']==request.printing),None)
                if reference_card is None: raise ResearchUnavailable('reference_not_standard')
                reference=reference_card['functional_identity']
                row=dbs['cards'].execute('SELECT raw FROM cards WHERE id=?',(request.printing,)).fetchone()
                raw=json.loads(row['raw'])
                if request.variant and not raw.get('variants',{}).get(request.variant):
                    raise ResearchUnavailable('context_unavailable')
            if request.include_deck:
                if 'workspace' in errors: raise ResearchUnavailable('context_unavailable')
                row=dbs['workspace'].execute('SELECT revision,document FROM workspace WHERE id=1').fetchone()
                if row is None or row['revision']!=request.revision: raise ResearchUnavailable('context_changed')
                doc=json.loads(row['document']);entries=[]
                by_printing={c['printing']:c for c in index.cards}
                for entry in sorted(doc['entries'],key=lambda e:e['identity']):
                    printings=sorted(a['printing_id'] for a in entry['allocations'])
                    card=next((by_printing[p] for p in printings if p in by_printing),None)
                    # No guessed identity/name for unresolved or non-Standard entries.
                    entries.append(dict(identity=entry['identity'],quantity=entry['quantity'],
                        name=card['name'] if card else None,functional_id=card['functional_identity'] if card else None))
                    if card: deck_ids.append((entry['quantity'],card['functional_identity']))
                active=dict(id='active-deck',name=doc['name'],revision=row['revision'],dirty=doc['dirty'],
                    content_hash=digest(doc),entries=entries,references=[])
    except (Unavailable,OSError,ValueError) as exc:
        raise ResearchUnavailable('context_unavailable') from None
    if stamp(sources.paths['cards'])!=before: raise ResearchUnavailable('inconsistent_snapshot')
    question=normalize(request.question)
    boundary=None
    if re.search(r'\b(matchup|piloting|tactics)\b|how (?:should|do) i play.*(?:against|versus)|\b(?:replace|cut|save|edit|add)\b.*\b(?:deck|card)\b',question):
        boundary='Detailed piloting, matchup plans and deck-changing actions are outside this research scope.'
    lookup=query_text(request.question,reference)
    queries=[lookup]
    inferred=False;anchor_ids=[]
    if request.include_deck and not parse_query(lookup)['concepts'] and re.search(r'support.*deck|mechanics in this deck',question):
        # Bounded orientation from printed mechanics, not inferred pilot intent.
        concepts=[]
        for _,fid in sorted(deck_ids,key=lambda p:(-p[0],p[1])):
            for e in index.by_identity[fid]:
                for concept in e.mechanics:
                    if concept in BY_CONCEPT and concept not in {'draw','pokemon_ex_interaction','rule_box_interaction'} and concept not in concepts:
                        concepts.append(concept)
                        if len(concepts)<=3 and fid not in anchor_ids: anchor_ids.append(fid)
        queries=[c.replace('_',' ') for c in concepts[:3]]
        # Use known parseable query aliases, never arbitrary concept-to-prose NLP.
        aliases={'opponent_mill':'mill my opponent','self_mill':'mill me','pokemon_recovery':'recover Pokémon from discard pile',
            'damage_counter_movement':'move damage counters','bench_damage':'damage the bench','copy_effect':'copy attacks',
            'item_lock':'item lock','ability_lock':'ability lock','tool_nullification':'tool effect suppression'}
        queries=[aliases.get(c,c.replace('_',' ')) for c in concepts[:3]]
        inferred=True
    results=[];seen=set();retrievals=[]
    if not boundary:
        for query in queries:
            result=index.search(query,reference,limit=10);retrievals.append(result)
        # Round-robin for deck-context orientations; original score preserved.
        for rank in range(10):
            for result in retrievals:
                if rank<len(result['results']):
                    candidate=result['results'][rank]
                    if candidate['functional_identity'] not in seen:
                        seen.add(candidate['functional_identity']);results.append(candidate)
    evidence=[];refs=[];omitted=['competitive-evidence:not-projected;mechanical-relevance-is-not-tournament-success',
        'candidate-cap-5;component-cap-2;complete-retrieval-output-not-sent']
    def item(kind,payload,source_refs=()):
        return Item(id='ev-pool-'+digest(dict(kind=kind,payload=payload))[:24],kind=kind,
            classification='SOURCE_FACT' if kind=='card-pool-candidate' else 'DERIVED_FACT',
            fields=fields(payload),references=tuple(source_refs))
    def project(candidate,kind='card-pool-candidate'):
        components=[];component_keys=set();source_refs=[]
        for match in candidate['components']:
            e=match['effect'];key=(e['component'],e['component_index'],e['normalized_text'])
            if key in component_keys: continue
            component_keys.add(key)
            ref=Reference(id='ref-pool-'+e['source_card_hash'],source='TCGdex',resource=e['printing'],
                url=e['source_url'],checked_at=e['checked_at'],content_hash=e['source_card_hash'])
            source_refs.append(ref.id)
            if ref not in refs: refs.append(ref)
            components.append(dict(component=e['component'],name=e['component_name'],text=e['raw_text'],
                normalized_text=e['normalized_text'],structured=json.loads(e['structured_json']),
                atoms=match['matched_atoms'],concepts=match['matched_concepts'],related=match['related_concepts'],
                matched_text=match['matched_text'],representation=e['representation'],ambiguities=e['ambiguities'],
                source_issues=e['source_issues'],unmatched_spans=e['unmatched_spans']))
            if len(components)==COMPONENT_CAP: break
        return item(kind,dict(name=candidate['name'],functional_identity=candidate['functional_identity'],
            printing=candidate['representative']['printing'],standard=True,category=candidate['category'],
            properties=candidate['source_fields'],classification=candidate['classification'],score=candidate['score'],
            score_components=candidate['score_components'],components=components,
            constraints_satisfied=candidate['constraints_satisfied'],constraints_unevaluable=candidate['constraints_unevaluable']),source_refs)
    def context_card(card,kind,variant=None):
        source_effects=[e for e in index.by_identity[card['functional_identity']] if e.printing==card['printing']]
        ref=Reference(id='ref-pool-'+card['source_hash'],source='TCGdex',resource=card['printing'],
            url='https://api.tcgdex.net/v2/en/cards/'+card['printing'],checked_at=card['checked_at'],content_hash=card['source_hash'])
        if ref not in refs: refs.append(ref)
        return item(kind,dict(name=card['name'],printing=card['printing'],variant=variant,
            functional_identity=card['functional_identity'],standard=True,
            components=[dict(component=e.component,name=e.component_name,text=e.raw_text,structured=json.loads(e.structured_json)) for e in source_effects][:2]),(ref.id,))
    if reference_card: evidence.append(context_card(reference_card,'reference-card',request.variant))
    for fid in anchor_ids: evidence.append(context_card(index.groups[fid][0],'deck-mechanics'))
    for candidate in results[:CAP]: evidence.append(project(candidate))
    def assemble():
        used={r for e in evidence for r in e.references}
        packet=PoolPacket(request=dict(question=request.question,printing=request.printing,variant=request.variant,
            window=request.window,as_of=str(today or date.today())),
            query=dict(retrieval_queries=queries,representations=[r['query'] for r in retrievals],
                deck_orientation_inferred=inferred,orientation_is_not_creator_intent=True),corpus_hash=index.corpus_hash,
            evidence=tuple(evidence),references=tuple(r for r in refs if r.id in used),
            coverage=Coverage(requested=('card-pool',),included=tuple(e.kind for e in evidence),omitted=tuple(omitted),
                unavailable=('tournament-performance','piloting-guides','reviewed-gameplay-result')))
        envelope=PoolEnvelope(packet=packet,active_deck=active,omitted=(),boundary=boundary,content_hash='',
            catalog_names=tuple(sorted({c['name'] for c in index.cards})))
        return envelope.model_copy(update={'content_hash':digest(envelope.model_dump(mode='json',exclude={'content_hash'}))})
    envelope=assemble()
    while len(canonical(envelope).encode())>BYTES and any(e.kind=='card-pool-candidate' for e in evidence):
        evidence.pop();omitted.append('candidate:byte-budget');envelope=assemble()
    if len(canonical(envelope).encode())>BYTES: raise ResearchUnavailable('budget_exceeded')
    return envelope


def violation(answer,envelope):
    """Additional bounded guards; not a universal natural-language entailment proof."""
    from .research_grounding import fields
    supplied={e.id:fields(e.model_dump(mode='json')['fields']) for e in envelope.packet.evidence}
    available={v['name'] for v in supplied.values() if v.get('name')}
    available.update(e['name'] for e in envelope.active_deck.get('entries',[]) if e.get('name'))
    unsupported=set(envelope.catalog_names)-available
    for statement in (*answer.facts,*answer.interpretation):
        text=statement.text
        cited=[supplied[r] for r in statement.evidence if r in supplied]
        for clause in re.split(r'[.!?;]|\bbut\b|\bhowever\b',text,flags=re.I):
            if re.search(r'\b(?:best|top-tier|premier|tournament staple|most reliable|meta choice|proven|successful|competitive)\b',clause,re.I) and not re.search(r"\b(?:not|isn't|cannot|can't|doesn't|unproven|unavailable|unknown)\b",clause,re.I):
                return 'unsupported_competitive_claim'
        if re.search(r'\b(?:replace|cut|add|save|edit)\b.*\b(?:deck|copies|with)\b|\byou should (?:play|attack|retreat)\b',text,re.I):
            return 'unsupported_action_or_piloting'
        for name in unsupported:
            if len(name)>=4 and re.search(r'\b'+re.escape(name)+r'\b',text) and not any(name in n for n in available):
                return 'candidate_outside_evidence'
        for value in supplied.values():
            name=value.get('name')
            if name and name.casefold() in text.casefold() and not any(v.get('name')==name for v in cited):
                return 'uncited_candidate_claim'
        if statement in answer.facts and not cited and statement.evidence!=('active-deck',):
            return 'unsupported_candidate_fact'
        for v in cited:
            components=v.get('components',[])
            raw=' '.join(c.get('text') or '' for c in components).casefold()
            from .research_grounding import COST, WORDS
            for component in components:
                attack=component.get('structured',{})
                if component.get('component')!='attack' or not component.get('name') or component['name'].casefold() not in text.casefold(): continue
                claims=COST.findall(text)
                if re.search(r'\b(?:is free|zero-cost|requires no energy|costs no energy)\b',text,re.I): claims.append('zero')
                for claim in claims:
                    number=int(claim) if claim.isdigit() else WORDS[claim.lower()]
                    if not isinstance(attack.get('cost'),list) or len(attack['cost'])!=number: return 'unsupported_attack_cost'
            if v.get('classification') in ('related_functional','text_only_uncertain') and re.search(r'\b(?:directly|same mechanic|equivalent)\b',text,re.I):
                return 'unsupported_match_equivalence'
            if re.search(r'mills? (?:your |the |my )?opponent|opponent.s deck',text,re.I) and 'opponent' not in raw:
                return 'unsupported_mill_direction'
            if re.search(r'\btools\b',text,re.I) and 'tool' not in raw:
                return 'unsupported_tool_claim'
            # Numeric card properties cannot be invented from retrieval rank.
            if re.search(r'\b\d+\s*(?:hp|damage|energy)\b',text,re.I):
                numbers=re.findall(r'\b\d+\b',text)
                source=json.dumps(components)+json.dumps(v.get('properties',{}))
                if any(not re.search(r'\b'+n+r'\b',source) for n in numbers): return 'unsupported_numeric_card_claim'
    return None
