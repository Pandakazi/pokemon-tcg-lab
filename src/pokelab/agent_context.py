"""Deterministic selected-card retrieval. No provider, planner, network or writes."""
import json
import math
import sqlite3
from .agent_context_models import (Request, Packet, Budget, Coverage, Evidence, Reference, FieldValue,
    CardFacts, DeckFacts, OwnershipFacts, OwnedFinish, CompetitiveFacts, ArchetypeFact, AssociationFact,
    ObservationFacts, CompositeFacts)
from .agent_context_sources import SnapshotCards, SnapshotCollection, SnapshotCompetitive, Unavailable
from .agent_rules_view import rules_view
from .collection import Collection
from .decks import Decks, deck_identity, check_allocations
from .research import Research
from .rules.models import digest


def canonical(value):
    return json.dumps(value.model_dump(mode='json') if hasattr(value,'model_dump') else value,
                      sort_keys=True, ensure_ascii=False, separators=(',',':'))


def finish(request, evidence, references, requested, omitted, unavailable, cap, status=None):
    """Hash excludes only its own field; measured size includes the entire packet."""
    def assemble(items, why, forced=None):
        used = {r for item in items for r in item.references}
        refs = tuple(sorted((r for r in references if r.id in used), key=lambda r:r.id))
        if used != {r.id for r in refs}: raise ValueError('Unresolved evidence reference')
        size = 0
        for _ in range(12):
            packet = Packet(status=forced or status or ('partial' if unavailable else 'ready'), request=request,
                content_hash='0'*64, evidence=tuple(items), references=refs,
                coverage=Coverage(requested=tuple(requested), included=tuple(i.payload.kind for i in items),
                                  omitted=tuple(why), unavailable=tuple(unavailable)),
                budget=Budget(cap_bytes=cap,serialized_bytes=size,estimated_tokens=math.ceil(size/4),evidence_count=len(items)))
            value=packet.model_dump(mode='json'); value.pop('content_hash')
            packet=packet.model_copy(update={'content_hash':digest(value)})
            measured=len(canonical(packet).encode('utf-8'))
            if measured==size: return packet
            size=measured
        raise ValueError('Size accounting did not converge')
    packet=assemble(evidence,omitted)
    # Optional observations/composite/competitive are dropped as complete items,
    # including provenance. Never trim denominators, statuses or limitations.
    items=list(evidence); why=list(omitted)
    for kind in ('observation','composite','competitive'):
        if packet.budget.serialized_bytes <= cap: break
        removed=[i for i in items if i.payload.kind==kind]
        if removed:
            items=[i for i in items if i.payload.kind!=kind]; why.append(kind+':budget')
            packet=assemble(items,why)
    if packet.budget.serialized_bytes > cap:
        packet=assemble([],['all-evidence:budget-exceeded'], 'budget_exceeded')
    if packet.budget.serialized_bytes > cap: raise ValueError('Request exceeds minimum packet budget')
    return packet


def build(request: Request, sources, *, cap_bytes=24576, trusted_rules=None):
    request=Request.model_validate(request.model_dump())
    if type(cap_bytes) is not int or not 4096 <= cap_bytes <= 24576: raise ValueError('Budget must be 4096..24576 bytes')
    items, refs, omissions, unavailable = [], [], [], []
    requested=['card','deck','ownership','competitive','rules']
    if request.archetype or request.observation: requested.append('observation')
    if request.include_composite: requested.append('composite')

    def reference(source, resource, content, **fields):
        r=Reference(id='ref-'+digest([source,resource,content])[:16], source=source,resource=resource,
                    content_hash=digest(content),**fields)
        if not any(x.id==r.id for x in refs): refs.append(r)
        return r.id

    def add(classification, payload, references):
        items.append(Evidence(id='ev-'+digest([classification,payload.model_dump(mode='json'),references])[:16],
                              classification=classification,payload=payload,references=tuple(references)))

    def unavailable_section(section):
        unavailable.append(section+':unavailable-or-incompatible')

    try:
        with sources.snapshot() as (dbs, errors):
            unavailable.extend(k+':'+v for k,v in sorted(errors.items()))
            if 'cards' not in dbs:
                return finish(request,[],[],requested,requested,unavailable,cap_bytes)
            cards=SnapshotCards(sources.paths['cards'],dbs['cards'])
            # Catalog uses certified identity calculations, without snapshot initialization.
            catalog_owner=Collection(cards,sources.paths['collection'])
            try:
                catalog=catalog_owner.catalog(); record=catalog[0][request.printing]; raw=record['card']
                card_key=deck_identity(record); fid=record['functional_id']
                fields=('category','hp','types','stage','abilities','attacks','effect','trainerType','energyType','retreat','regulationMark','legal')
                printed=tuple(FieldValue(field=k,value=canonical(raw[k])) for k in fields if k in raw)
                card_ref=reference('TCGdex',request.printing,raw,checked_at=record['checked_at'],
                                   url='https://api.tcgdex.net/v2/en/cards/'+request.printing)
                add('SOURCE_FACT',CardFacts(printing=request.printing,functional_id=fid,deck_identity=card_key,
                                           name=raw['name'],printed=printed),(card_ref,))
            except (KeyError, ValueError, OSError, sqlite3.Error):
                unavailable_section('selected-card')
                return finish(request,[],[],requested,requested,unavailable,cap_bytes)
            if 'workspace' in dbs:
                try:
                    row=dbs['workspace'].execute('SELECT revision,document FROM workspace WHERE id=1').fetchone()
                    if row is None or type(row['revision']) is not int or row['revision']<0: raise ValueError('Workspace missing')
                    document=json.loads(row['document']); check_allocations(document)
                    if type(document['dirty']) is not bool: raise ValueError('Invalid dirty state')
                    # Validate each allocation's existing deck identity; never repair it.
                    for entry in document['entries']:
                        for allocation in entry['allocations']:
                            if deck_identity(catalog[0][allocation['printing_id']]) != entry['identity']:
                                raise ValueError('Allocation identity mismatch')
                    validation=Decks(catalog_owner,sources.paths['workspace']).validation(document)
                    deck_ref=reference('deck-workspace','active',document,version='2')
                    add('DERIVED_FACT',DeckFacts(revision=row['revision'],content_hash=digest(document),dirty=document['dirty'],
                        total=validation['total'],categories=tuple(FieldValue(field=k,value=str(v)) for k,v in sorted(validation['categories'].items())),
                        validation_state=validation['state'],reasons=tuple(validation['reasons']),unknown=tuple(validation['unknown']),
                        limitations=tuple(validation['limitations']),selected_quantity=sum(e['quantity'] for e in document['entries'] if e['identity']==card_key),
                        functional_entries=len(document['entries'])),(deck_ref,card_ref))
                except (KeyError,TypeError,ValueError,OSError,sqlite3.Error): unavailable_section('deck')
            collection=None
            if 'collection' in dbs:
                collection=SnapshotCollection(cards,sources.paths['collection'],dbs['collection'])
                try:
                    snapshot=collection.snapshot()
                    variants=(request.variant,) if request.variant else tuple(sorted(snapshot.variants(request.printing)))
                    for variant in variants: snapshot.validate_variant(request.printing,variant)
                    owned=OwnershipFacts(printing=request.printing,functional_id=fid,functional_total=snapshot.functional_totals.get(fid,0),
                                         exact=tuple(OwnedFinish(finish=v,quantity=snapshot.ownership(request.printing,v)['quantity']) for v in variants))
                    ref=reference('collection','selected-ownership',owned.model_dump(mode='json'),version='1')
                    add('SOURCE_FACT',owned,(ref,card_ref))
                except (KeyError,TypeError,ValueError,OSError,sqlite3.Error):
                    collection=None; unavailable_section('ownership')
            competitive=None
            if 'competitive' in dbs:
                try:
                    competitive=SnapshotCompetitive(cards,sources.paths['competitive'],dbs['competitive'],sources.format_start)
                    stats=competitive.stats(fid,request.window,today=request.as_of,include_trend=False,card_catalog=catalog)
                    ranked=stats['top_archetypes']
                    if request.archetype:
                        focus=[a for a in stats['archetypes'] if a['research_id']==request.archetype]
                        ranked=focus+[a for a in ranked if a['research_id']!=request.archetype]
                    archetypes=ranked[:3]; partners=stats['associated_cards'][:5]
                    if len(stats['top_archetypes'])>3: omissions.append('archetypes:ranked-cap-3')
                    if len(stats['associated_cards'])>5: omissions.append('associations:ranked-cap-5')
                    provenance=reference('limitless-main','selected-card-aggregate',
                        {k:stats[k] for k in ('functional_id','period_start','period_end','sample_size','included_decks','published_decklists','excluded_unmapped','provenance')},
                        checked_at=stats['last_updated'],version=stats['parser_version'],
                        excerpt='Cached published mapped lists; observational evidence, not win rate or causation.')
                    event_refs=[reference('limitless-main',e['id'],e,event_date=e['date'],checked_at=e['fetched_at'],url=e['url'],version=stats['parser_version'])
                                for e in sorted(stats['provenance'],key=lambda e:(e['date'],e['id']))]
                    # Event reference count is bounded too. Aggregate fingerprint covers full provenance.
                    if len(event_refs)>3: omissions.append('event-references:cap-3')
                    names=('status','period_start','period_end','sample_size','included_decks','usage_percent','average_copies',
                           'published_decklists','excluded_unmapped','results_without_lists','tournament_count','source_error')
                    payload=CompetitiveFacts(**{k:stats[k] for k in names},prevalence_min_decks=stats['archetype_prevalence_min_decks'],
                        distribution=tuple(FieldValue(field=b['copies'],value=canonical({'decks':b['decks'],'percent':b['percent']})) for b in stats['copy_distribution']),
                        archetypes=tuple(ArchetypeFact(id=a['research_id'],name=a['name'],included=a['decks'],eligible=a['eligible_decks'],
                                                     prevalence_percent=a['prevalence_percent'],status=a['status']) for a in archetypes),
                        associations=tuple(AssociationFact(**{k:a[k] for k in ('functional_id','name','decks','cooccurrence_percent','conservative_lift')}) for a in partners),
                        limitations=('Cached published mapped lists only; not a field census, win rate or causal evidence.',
                                     'Archetype prevalence below 15 decks remains unknown.'))
                    add('EMPIRICAL_EVIDENCE',payload,(provenance,*event_refs[-3:]))
                except (KeyError,TypeError,ValueError,OSError,sqlite3.Error):
                    competitive=None; unavailable_section('competitive')
            if request.archetype or request.observation or request.include_composite:
                if collection is None or competitive is None: unavailable_section('research')
                else:
                    research=Research(competitive,collection)
                    try:
                        observations=[request.observation] if request.observation else [d['id'] for d in
                            research.evidence_page(request.archetype,request.window,page_size=3,today=request.as_of)['decks']]
                        for key in observations:
                            deck=research.tournament_deck(key); o=deck['observation']
                            if o['date']>request.as_of.isoformat(): raise ValueError('Observation after as_of')
                            ref=reference('limitless-main',key,{'observation':o,'pages':deck['pages']},checked_at=o['fetched_at'],event_date=o['date'],
                                          url=o['source_url'],excerpt=canonical(deck['pages']))
                            add('EMPIRICAL_EVIDENCE',ObservationFacts(key=key,event=o['event_id'],date=o['date'],placement=o['placement'],archetype=o['archetype'],
                                mapped=o['mapped'],selected_quantity=sum(c['quantity'] for c in deck['cards'] if c['functional_id']==fid)),(ref,))
                        if request.include_composite:
                            if not request.archetype: raise ValueError('Composite requires explicit archetype')
                            composite=research.composite(request.archetype,request.window,today=request.as_of)
                            ref=reference('limitless-main',request.archetype+':composite',composite,version=composite['algorithm'])
                            add('DERIVED_FACT',CompositeFacts(archetype=request.archetype,**{k:composite[k] for k in
                                ('algorithm','status','sample_size','limited_evidence','total','reasons','limitations')},
                                selected_quantity=sum(c['quantity'] for c in composite['cards'] if c['functional_id']==fid)),(ref,))
                    except (KeyError,TypeError,ValueError,OSError,sqlite3.Error): unavailable_section('research')
            try:
                rules, rules_refs=rules_view(cards,request.printing,trusted_rules)
                refs.extend(rules_refs)
                add('RULES_RESULT',rules,tuple(r.id for r in rules_refs) or (card_ref,))
            except (KeyError,TypeError,ValueError,OSError,sqlite3.Error): unavailable_section('rules')
    except Unavailable:
        return finish(request,[],[],requested,requested,['inconsistent_snapshot'],cap_bytes,'inconsistent_snapshot')
    return finish(request,items,refs,requested,omissions,unavailable,cap_bytes)
