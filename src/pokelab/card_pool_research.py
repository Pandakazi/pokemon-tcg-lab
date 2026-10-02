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


def numeric_supported(text, value):
    """Check bounded numeric forms against their own fields, not a bag of digits.

    Printed effects remain source text, not an executable mechanics model.
    Unknown/ambiguous quantities fail rather than borrowing an unrelated number.
    """
    from collections import Counter
    from .research_grounding import WORDS
    def normalized(s):
        s=re.sub(r'\b('+ '|'.join(WORDS)+r')\b',lambda m:str(WORDS[m[0].lower()]),s,flags=re.I)
        return re.sub(r'\bstage(\d+)\b',r'stage \1',s,flags=re.I)
    text=normalized(text)
    components=value.get('components',[])
    named=[c for c in components if c.get('name') and c['name'].casefold() in text.casefold()]
    components=named or components
    attacks=[c.get('structured',{}) for c in components if c.get('component')=='attack']
    raw=normalized(' '.join(c.get('text') or '' for c in components))
    energy_types=r'Fire|Water|Grass|Lightning|Psychic|Fighting|Darkness|Metal|Dragon|Colorless'
    units=re.compile(r'\b(\d+)\s+(HP|damage|Energy|'+energy_types+r')(?:\s+Energy)?\b(?!\s+(?:counters?|cards?)\b)',re.I)
    quantities=re.compile(r'\b(?:discards?|mills?|removes?)\s+(?:the top\s+)?(\d+)\b(?:\s+cards?\b)?',re.I)
    printed_quantities=re.findall(r'\bdiscard\s+(?:the top\s+)?(\d+)\s+cards?\b',raw,re.I)
    if re.search(r'\bdiscard the top card\b',raw,re.I): printed_quantities.append('1')
    spans=[]
    for match in units.finditer(text):
        number=int(match[1]);unit=match[2].casefold()
        if unit=='hp': valid=str(value.get('properties',{}).get('hp'))==str(number)
        elif unit=='damage': valid=bool(attacks) and all(str(a.get('damage'))==str(number) for a in attacks)
        else:
            valid=bool(attacks) and all(isinstance(a.get('cost'),list) and (
                len(a['cost'])==number if unit=='energy' else
                Counter(str(t).casefold() for t in a['cost'])[unit]==number) for a in attacks)
        if not valid: return False
        spans.append(match.span())
    for match in quantities.finditer(text):
        if match[1] not in printed_quantities: return False
        spans.append(match.span())
    for match in re.finditer(r'\b(\d+)\s+(?:coin flips?|coins?)\b',text,re.I):
        if not re.search(r'\bflip\s+'+match[1]+r'\s+coins?\b',raw,re.I): return False
        spans.append(match.span())
    remaining=text
    for start,end in sorted(spans,reverse=True): remaining=remaining[:start]+' '+remaining[end:]
    # Retain the conservative numeric check for other wording, with counts
    # derived only from this cited card's explicit structured cost arrays.
    source=normalized(json.dumps(components)+json.dumps(value.get('properties',{})))
    for attack in attacks:
        if isinstance(attack.get('cost'),list):
            source+=' '+str(len(attack['cost']))+' '+' '.join(map(str,Counter(attack['cost']).values()))
    return all(re.search(r'\b'+n+r'\b',source) for n in re.findall(r'\b\d+\b',remaining))


def violation(answer,envelope,diagnostics=None):
    """Bounded checks scoped to the cited subject of each sentence/clause.

    A validated attack-cost operand is not a recommendation of an Energy card.
    Numeric costs are checked against the cost array, not JSON digit occurrence.
    No prose, unknown identifier or arbitrary value enters diagnostics.
    """
    from .research_grounding import fields, COST, WORDS
    supplied={e.id:fields(e.model_dump(mode='json')['fields']) for e in envelope.packet.evidence}
    available={v['name'] for v in supplied.values() if v.get('name')}
    available.update(e['name'] for e in envelope.active_deck.get('entries',[]) if e.get('name'))
    unsupported=sorted(set(envelope.catalog_names)-available)
    for field in ('facts','interpretation'):
        for index,statement in enumerate(getattr(answer,field)):
            cited=[supplied[r] for r in statement.evidence if r in supplied]
            def fail(condition,clause_index=0):
                if diagnostics is not None:
                    diagnostics.update(stage='card_pool_grounding',path=[field,index,'text'],
                        clause_index=clause_index,cited_evidence_ids=[r for r in statement.evidence if r in supplied],
                        cited_evidence_count=len(cited))
                return condition
            # Citation membership is checked by assess before this function.
            for value in supplied.values():
                name=value.get('name')
                if name and name.casefold() in statement.text.casefold() and not any(v.get('name')==name for v in cited):
                    return fail('uncited_candidate_claim')
            if field=='facts' and not cited and statement.evidence!=('active-deck',):
                return fail('unsupported_candidate_fact')
            clauses=[]
            names='|'.join(re.escape(v['name']) for v in cited if v.get('name'))
            for sentence in re.split(r'(?<=[.!?;])\s+|\s+(?:whereas|while)\s+',statement.text,flags=re.I):
                start=0
                # Split a new explicit card subject after an existing numeric
                # predicate. Keep shared subjects ("X and Y mill 2") together
                # so both must support the shared value; never pool numbers.
                if names:
                    for boundary in re.finditer(r'(?:,\s*(?:(?:and|but)\s+)?|\s+(?:and|but|versus)\s+)(?=(?:'+names+r')\b)',sentence,re.I):
                        if re.search(r'\b(?:\d+|'+ '|'.join(WORDS)+r')\b',sentence[start:boundary.start()],re.I):
                            clauses.append(sentence[start:boundary.start()]);start=boundary.end()
                clauses.append(sentence[start:])
            for clause_index,text in enumerate(clauses):
                named=[v for v in cited if v.get('name','').casefold() in text.casefold() or any(
                    c.get('name') and c['name'].casefold() in text.casefold() for c in v.get('components',[]))]
                relevant=named or cited  # Unresolved subject remains conservative.
                for qualification in re.split(r'\s+(?:but|however)\s+',text,flags=re.I):
                    if re.search(r"\b(?:best|top-tier|premier|tournament staple|most reliable|meta choice|proven|successful|competitive)\b",qualification,re.I) and not re.search(r"\b(?:not|isn't|cannot|can't|doesn't|unproven|unavailable|unknown)\b",qualification,re.I):
                        return fail('unsupported_competitive_claim',clause_index)
                if re.search(r'\b(?:replace|cut|add|save|edit)\b.*\b(?:deck|copies|with)\b|\byou should (?:play|attack|retreat)\b',text,re.I):
                    return fail('unsupported_action_or_piloting',clause_index)
                attacks=[c['structured'] for v in relevant for c in v.get('components',[])
                    if c.get('component')=='attack' and c.get('name') and c['name'].casefold() in text.casefold()]
                if not attacks and named:
                    # A named card with exactly one projected attack has an
                    # unambiguous cost source even without the attack's name.
                    candidates=[[c['structured'] for c in v.get('components',[]) if c.get('component')=='attack'] for v in named]
                    if all(len(group)==1 for group in candidates): attacks=[group[0] for group in candidates]
                costs=list(COST.finditer(text))
                free=bool(re.search(r'\b(?:is free|zero-cost|requires no energy|costs no energy)\b',text,re.I))
                if costs or free:
                    # A shared, ambiguous cost assertion must agree with every
                    # named attack; separate clauses can have different costs.
                    if not attacks: return fail('unsupported_attack_cost',clause_index)
                    for match in costs:
                        claim=match.group(1);number=int(claim) if claim.isdigit() else WORDS[claim.lower()]
                        typed=re.search(r'\b(Fire|Water|Grass|Lightning|Psychic|Fighting|Darkness|Metal|Dragon|Colorless) Energy',match.group(),re.I)
                        for attack in attacks:
                            cost=attack.get('cost')
                            if not isinstance(cost,list) or (not typed and len(cost)!=number):
                                return fail('unsupported_attack_cost',clause_index)
                            if typed and sum(str(t).casefold()==typed.group(1).casefold() for t in cost)!=number:
                                return fail('unsupported_attack_cost',clause_index)
                    if free and any(a.get('cost')!=[] for a in attacks):
                        return fail('unsupported_attack_cost',clause_index)
                # Remove ONLY fully validated cost operands before catalog-name
                # and numeric-claim checks. Other occurrences still get checked.
                remaining=text
                for match in reversed(costs): remaining=remaining[:match.start()]+' '+remaining[match.end():]
                for name in unsupported:
                    if len(name)>=4 and re.search(r'\b'+re.escape(name)+r'\b',remaining) and not any(name in n for n in available):
                        return fail('candidate_outside_evidence',clause_index)
                for value in relevant:
                    components=value.get('components',[])
                    raw=' '.join(c.get('text') or '' for c in components).casefold()
                    if value.get('classification') in ('related_functional','text_only_uncertain') and re.search(r'\b(?:directly|same mechanic|equivalent)\b',text,re.I):
                        return fail('unsupported_match_equivalence',clause_index)
                    if re.search(r'mills? (?:your |the |my )?opponent|opponent.s deck',text,re.I) and 'opponent' not in raw:
                        return fail('unsupported_mill_direction',clause_index)
                    if re.search(r'\btools\b',text,re.I) and 'tool' not in raw:
                        return fail('unsupported_tool_claim',clause_index)
                    if not numeric_supported(remaining,value):
                        return fail('unsupported_numeric_card_claim',clause_index)
    return None
