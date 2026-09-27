"""Pass 1: immutable local deck evidence. No API, provider, interpretation or writes."""
from collections import Counter
from datetime import date
import json
import re
from statistics import median
from typing import Literal
import unicodedata

from pydantic import Field
from .agent_context import canonical
from .agent_context_models import Frozen, FieldValue, Reference, Coverage
from .agent_context_sources import SnapshotCards, SnapshotCollection, SnapshotCompetitive, Unavailable
from .competitive import ARCHETYPE_PREVALENCE_MIN_DECKS
from .decks import check_allocations, deck_identity
from .research import Research
from .limitless_main import SOURCE
from .rules.models import digest

EVIDENCE_BYTES = 24 * 1024
FUTURE_ENVELOPE_BYTES = 32 * 1024  # Reserved; no provider envelope in Pass 1.
CORE_PERCENT, COMMON_PERCENT, UNCOMMON_PERCENT = 80, 50, 25
TYPICAL_MASS_PERCENT = 80
CORE_ORIENTATION_CAP = 3
CAPS = (('composition', 12), ('mechanics', 6), ('comparison', 10), ('deviation', 10))
INTENTS = ('DECK_OVERVIEW', 'ARCHETYPE_COMPARISON', 'CARD_ROLE', 'CARD_QUANTITY',
           'PRESENT_DEVIATIONS', 'ABSENT_CARDS', 'MECHANICAL_INTERACTION',
           'COMPETITIVE_CONTEXT', 'CREATOR_INTENT', 'UNKNOWN')
PRINTED = ('category', 'types', 'stage', 'evolveFrom', 'abilities', 'attacks',
           'effect', 'energyType', 'trainerType', 'rarity')


class Card(Frozen):
    identity: str
    name: str
    quantity: int
    category: str
    printing: str
    energy_type: str | None = None
    ace_spec: bool | None = None
    evolves_from: str | None = None
    evolution_parents: tuple[str, ...] = ()
    printed: tuple[FieldValue, ...]
    reference: Reference


class Bucket(Frozen):
    quantity: int
    lists: int


class Comparison(Frozen):
    identity: str
    name: str
    active_quantity: int
    eligible_lists: int
    lists_including: int
    inclusion_rate: float | None
    mean_quantity_when_included: float | None
    median_quantity_when_included: float | None
    modes: tuple[int, ...]
    typical_range: tuple[int, int] | None
    observed_range: tuple[int, int] | None
    distribution: tuple[Bucket, ...]
    characteristics: tuple[str, ...]


class Population(Frozen):
    source: Literal['limitless-main'] = SOURCE
    source_archetype: str | None = None
    archetype: str | None
    name: str | None
    selection_basis: Literal['explicit-local-archetype', 'unavailable']
    window: str
    as_of: date
    status: str
    period_start: str | None = None
    period_end: str
    published_lists: int = 0
    eligible_lists: int = 0
    excluded_unmapped: int = 0
    excluded_current_identity: int = 0
    self_comparison: Literal['excluded_exactly', 'not_present', 'unavailable'] = 'unavailable'
    self_comparison_reason: str = 'source-list-identity-not-retained'
    active_observation: str | None = None
    excluded_self: int = 0
    excluded_self_reference: Reference | None = None
    results_without_lists: int = 0
    results_without_lists_scope: str = 'All cached tournaments in the window; not archetype-specific.'
    snapshot_hash: str
    references: tuple[Reference, ...] = ()


class Profile(Frozen):
    version: Literal['pokelab-deck-research-profile-v1'] = 'pokelab-deck-research-profile-v1'
    deck_id: str
    revision: int
    deck_hash: str
    name: str
    dirty: bool
    total: int
    categories: tuple[FieldValue, ...]
    cards: tuple[Card, ...]
    population: Population
    comparisons: tuple[Comparison, ...]
    matching_observations: tuple[FieldValue, ...] = ()
    unavailable: tuple[str, ...]
    configuration_hash: str
    content_hash: str


class Intent(Frozen):
    categories: tuple[str, ...]
    card_references: tuple[str, ...]


class Item(Frozen):
    id: str
    kind: str
    classification: Literal['SOURCE_FACT', 'DERIVED_FACT', 'EMPIRICAL_EVIDENCE', 'RULES_RESULT']
    identity: str | None = None
    fields: tuple[FieldValue, ...]
    references: tuple[str, ...]


class Packet(Frozen):
    version: Literal['pokelab-deck-research-evidence-v1'] = 'pokelab-deck-research-evidence-v1'
    profile_hash: str
    question: str = Field(min_length=1, max_length=2000)
    intent: Intent
    evidence: tuple[Item, ...]
    references: tuple[Reference, ...]
    coverage: Coverage
    cap_bytes: int = EVIDENCE_BYTES
    serialized_bytes: int
    content_hash: str


def configuration():
    return dict(version=2, core_percent=CORE_PERCENT, common_percent=COMMON_PERCENT,
                uncommon_percent=UNCOMMON_PERCENT, confidence_min=ARCHETYPE_PREVALENCE_MIN_DECKS,
                quantity_rule='outside-included-equal-tail-nearest-rank-band;positive-active-only',
                typical_mass_percent=TYPICAL_MASS_PERCENT,
                self_exclusion='validated-explicit-observation-id-and-exact-vector',
                caps=CAPS, core_orientation_cap=CORE_ORIENTATION_CAP,
                evidence_bytes=EVIDENCE_BYTES, ranking='intent-priority-then-identity-v1')


def fields(values):
    return tuple(FieldValue(field=k, value=canonical(v)) for k, v in sorted(values.items()))


def compare(identity, name, active, counts, confident=True):
    """Zeros are population evidence; positive quantities define the included range."""
    n = len(counts); buckets = Counter(counts); included = sorted(q for q in counts if q > 0)
    k = len(included); frequency = Counter(included)
    modes = tuple(sorted(q for q, count in frequency.items() if count == max(frequency.values()))) if k else ()
    # Empirical inverse CDF, nearest ranks: ceil(n*10/100), ceil(n*90/100).
    # Integer arithmetic, no interpolation; ties retain their entire quantity value.
    tail = (100-TYPICAL_MASS_PERCENT)//2
    band = (included[max(1,(k*tail+99)//100)-1], included[(k*(100-tail)+99)//100-1]) if k else None
    labels = []
    if n and confident:
        if 100*k >= CORE_PERCENT*n: labels.append('ARCHETYPE_CORE')
        if active and 100*k >= COMMON_PERCENT*n: labels.append('COMMON_PRESENT')
        if active and 100*k < UNCOMMON_PERCENT*n: labels.append('UNCOMMON_PRESENT')
        if not active and 100*k >= COMMON_PERCENT*n: labels.append('COMMON_ABSENT')
        if active and k:
            if active > band[1]: labels.append('ABOVE_TYPICAL_QUANTITY')
            if active < band[0]: labels.append('BELOW_TYPICAL_QUANTITY')
    return Comparison(identity=identity, name=name, active_quantity=active, eligible_lists=n,
        lists_including=k, inclusion_rate=k/n if n and confident else None,
        mean_quantity_when_included=sum(included)/k if k else None,
        median_quantity_when_included=median(included) if k else None, modes=modes,
        typical_range=band, observed_range=(included[0], included[-1]) if k else None,
        distribution=tuple(Bucket(quantity=q, lists=c) for q,c in sorted(buckets.items())),
        characteristics=tuple(labels))


def build_profile(sources, *, revision, as_of, archetype=None, window='30', active_observation=None):
    """Explicit as-of/archetype inputs; never infer archetype or creator from a name."""
    if window not in ('7', '30', '90', 'format'): raise ValueError('Unsupported window')
    with sources.snapshot() as (dbs, errors):
        if any(k in errors for k in ('cards','collection','workspace')):
            raise Unavailable('deck_context_unavailable')
        row = dbs['workspace'].execute('SELECT revision,document FROM workspace WHERE id=1').fetchone()
        if row is None or row['revision'] != revision: raise Unavailable('context_changed')
        document = json.loads(row['document']); check_allocations(document)
        cards = SnapshotCards(sources.paths['cards'], dbs['cards'])
        collection = SnapshotCollection(cards, sources.paths['collection'], dbs['collection'])
        records, functions, _ = collection.catalog()
        groups = {}
        for key, record in sorted(records.items()): groups.setdefault(deck_identity(record), []).append(key)
        active = Counter()
        for entry in document['entries']:
            if any(a['printing_id'] not in records or deck_identity(records[a['printing_id']]) != entry['identity'] for a in entry['allocations']):
                raise Unavailable('invalid_functional_allocation')
            active[entry['identity']] += entry['quantity']
        unavailable = ['creator_intent', 'semantic-functions:draw-search-acceleration-disruption-recovery', 'reviewed-interaction-results']
        header = None; selected = []; events = {}; vectors = []; refs = []; matches = []; excluded = 0
        if archetype and 'competitive' not in errors:
            research = Research(SnapshotCompetitive(cards,sources.paths['competitive'],dbs['competitive'],sources.format_start), collection)
            try: header, selected, events = research.selected(archetype, window, as_of)
            except KeyError: unavailable.append('archetype_not_in_local_cache')
            if header:
                for deck in sorted(selected, key=lambda d:(d['event_id'],d['rank'])):
                    if not deck['resolved']: continue
                    vector = Counter(); valid = True
                    for fid,q in sorted(deck['cards'].items()):
                        ids = functions.get(fid, ())
                        if not ids or type(q) is not int or q <= 0: valid = False; break
                        vector[deck_identity(records[sorted(ids)[0]])] += q
                    if not valid: excluded += 1; continue
                    vectors.append(dict(vector))
                    observation = research.observation(deck,events[deck['event_id']])
                    refs.append(Reference(id='ref-'+digest(observation), source=header['source'],
                        resource=observation['id'], url=observation['source_url'], checked_at=observation['fetched_at'],
                        event_date=observation['date'], content_hash=digest(dict(observation=observation,cards=dict(vector),raw=deck['raw']))))
                    # Exact vector equality is an observation match, never proof of copy provenance/intent.
                    if vector == active: matches.append(FieldValue(field=observation['id'],value=canonical(observation)))
        self_state='unavailable'; self_reason='source-list-identity-not-retained'; excluded_ref=None
        if active_observation:
            self_reason='source-list-identity-unverifiable'
            if header:
                try:
                    source=research.tournament_deck(active_observation)
                    source_vector=Counter()
                    for item in source['cards']:
                        ids=functions.get(item['functional_id'],())
                        if not ids: raise KeyError('unmapped')
                        source_vector[deck_identity(records[sorted(ids)[0]])]+=item['quantity']
                    if source['observation']['mapped'] and source_vector==active:
                        positions=[i for i,r in enumerate(refs) if r.resource==active_observation]
                        if len(positions)==1:
                            index=positions[0]; excluded_ref=refs.pop(index); vectors.pop(index)
                            self_state='excluded_exactly'; self_reason='validated-source-identity-and-vector'
                        elif not positions:
                            self_state='not_present'; self_reason='validated-source-not-in-eligible-population'
                    else: self_reason='source-composition-does-not-match-active-deck'
                except KeyError: pass
        if self_state=='unavailable': unavailable.append('self-exclusion:'+self_reason)
        if not header: unavailable.append('comparison_population')
        if header and header['source_error']: unavailable.append('competitive-cache-source-error')
        n = len(vectors)
        confident = bool(header and n >= ARCHETYPE_PREVALENCE_MIN_DECKS and header['source_id'] != 'unknown')
        if header and not confident: unavailable.append('prevalence-confidence:minimum-15-known-archetype')
        population = Population(source_archetype=header['source_id'] if header else None,
            archetype=header['id'] if header else None, name=header['name'] if header else None,
            selection_basis='explicit-local-archetype' if header else 'unavailable', window=window, as_of=as_of,
            status=('observed' if confident else 'limited_evidence' if n else header['status']) if header else 'unavailable',
            period_start=header['period_start'] if header else None, period_end=as_of.isoformat(),
            published_lists=header['published_decks'] if header else 0, eligible_lists=n,
            excluded_unmapped=header['excluded_unmapped'] if header else 0, excluded_current_identity=excluded,
            self_comparison=self_state,self_comparison_reason=self_reason,active_observation=active_observation,
            excluded_self=int(excluded_ref is not None),excluded_self_reference=excluded_ref,
            results_without_lists=header['results_without_lists'] if header else 0,
            snapshot_hash=digest(dict(header=header,vectors=vectors,references=[r.model_dump() for r in refs],
                active_observation=active_observation,self_comparison=self_state,self_reason=self_reason,
                excluded_reference=excluded_ref.model_dump() if excluded_ref else None)), references=tuple(refs))
        identities = sorted(set(active) | {fid for v in vectors for fid in v})
        output = []
        for fid in identities:
            printing = groups[fid][0]; record = records[printing]; raw = record['card']
            parent = raw.get('evolveFrom')
            parents = tuple(k for k in sorted(active) if parent and records[groups[k][0]]['card']['name']==parent)
            energy = fid.removeprefix('deck-basic-energy:') if fid.startswith('deck-basic-energy:') else raw.get('energyType')
            output.append(Card(identity=fid,name=raw['name'],quantity=active[fid],category=raw.get('category','Unknown'),
                printing=printing,energy_type=energy,ace_spec=('ACE SPEC' in raw['rarity'].upper()) if raw.get('rarity') else None,
                evolves_from=parent,evolution_parents=parents,printed=fields({k:raw[k] for k in PRINTED if k in raw}),
                reference=Reference(id='ref-card-'+digest(dict(printing=printing,card=raw)),source='TCGdex',resource=printing,
                    checked_at=record['checked_at'],content_hash=digest(raw))))
        comparisons = tuple(compare(c.identity,c.name,c.quantity,[v.get(c.identity,0) for v in vectors],confident) for c in output)
        categories = Counter()
        for c in output: categories[c.category] += c.quantity
        for name in ('Pokemon','Trainer','Energy'): categories.setdefault(name,0)
        profile = Profile(deck_id=document['id'],revision=revision,deck_hash=digest(document),name=document['name'],dirty=document['dirty'],
            total=sum(active.values()),categories=fields(dict(categories)),cards=tuple(output),population=population,
            comparisons=comparisons,matching_observations=tuple(matches),unavailable=tuple(sorted(set(unavailable))),
            configuration_hash=digest(configuration()),content_hash='')
        return profile.model_copy(update={'content_hash':digest(profile.model_dump(mode='json',exclude={'content_hash'}))})


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC',text).casefold().replace('’',"'").split())


def classify(question, profile):
    if not 1 <= len(question) <= 2000: raise ValueError('Question length outside bounds')
    q = normalize(question); found = set()
    references = tuple(sorted(c.identity for c in profile.cards if re.search(r'(?<!\w)'+re.escape(normalize(c.name))+r'(?!\w)',q)))
    if any(s in q for s in ('trying to do','overview','game plan','deck work','built around')): found.add('DECK_OVERVIEW')
    if any(s in q for s in ('typical','archetype','compare','differ','unusual')): found.add('ARCHETYPE_COMPARISON')
    if any(s in q for s in ('unusual','uncommon','stand out')): found.update(('PRESENT_DEVIATIONS','ARCHETYPE_COMPARISON'))
    if any(s in q for s in ('not playing','absent','missing','leave out')): found.update(('ABSENT_CARDS','ARCHETYPE_COMPARISON'))
    if any(s in q for s in ('why','role','purpose','point of')): found.add('CARD_ROLE')
    if re.search(r'\b(quantity|copies|copy|count|one|two|three|four|\d+)\b',q) and (references or 'card' in q):
        found.update(('CARD_QUANTITY','ARCHETYPE_COMPARISON'))
    if any(s in q for s in ('interact','mechanic','effect','ability','attack','work with')): found.add('MECHANICAL_INTERACTION')
    if any(s in q for s in ('tournament','competitive','popular','commonly','prevalence')): found.add('COMPETITIVE_CONTEXT')
    if re.search(r'\bwhy did\b|\bcreator\b|\bpilot intent\b',q): found.update(('CREATOR_INTENT','CARD_ROLE'))
    return Intent(categories=tuple(i for i in INTENTS if i in found) or ('UNKNOWN',),card_references=references)


def select_evidence(profile, question):
    if profile.configuration_hash != digest(configuration()):
        raise ValueError('Profile configuration differs; rebuild from the local snapshot')
    intent = classify(question,profile); categories = set(intent.categories); candidates = []
    population = profile.population
    deck_ref = Reference(id='ref-deck-'+profile.deck_hash,source='PokéLab workspace',resource=f'active-deck/revision/{profile.revision}',content_hash=profile.deck_hash)
    pop_ref = Reference(id='ref-population-'+population.snapshot_hash,source=SOURCE,
        resource=population.archetype or 'unavailable',content_hash=population.snapshot_hash, event_date=population.as_of.isoformat())
    references = {r.id:r for r in (deck_ref,pop_ref,*(c.reference for c in profile.cards))}
    def add(priority, kind, classification, identity, data, refs):
        item = Item(id='evidence-'+digest(dict(kind=kind,identity=identity,data=data)),kind=kind,
            classification=classification,identity=identity,fields=fields(data),references=tuple(refs))
        candidates.append((priority,identity or '',kind,item))
    add(-2,'deck','DERIVED_FACT',None,dict(deck_id=profile.deck_id,name=profile.name,revision=profile.revision,total=profile.total,
        categories=[v.model_dump() for v in profile.categories],profile_hash=profile.content_hash),[deck_ref.id])
    # Population metadata excludes full list provenance; the immutable profile retains every eligible list reference.
    add(-1,'population','EMPIRICAL_EVIDENCE',None,population.model_dump(mode='json',exclude={'references'}),[pop_ref.id])
    label_counts = Counter(label for row in profile.comparisons for label in row.characteristics)
    add(-0.5,'deviation-summary','DERIVED_FACT',None,dict(
        counts={label:label_counts[label] for label in ('ARCHETYPE_CORE','COMMON_PRESENT','UNCOMMON_PRESENT',
            'COMMON_ABSENT','ABOVE_TYPICAL_QUANTITY','BELOW_TYPICAL_QUANTITY')},
        configuration=configuration(),
        available=population.status=='observed'),[deck_ref.id,pop_ref.id])
    comparison = bool(categories & {'ARCHETYPE_COMPARISON','ABSENT_CARDS','PRESENT_DEVIATIONS','CARD_QUANTITY','COMPETITIVE_CONTEXT'})
    by_id = {c.identity:c for c in profile.cards}
    core = sorted((r for r in profile.comparisons if 'ARCHETYPE_CORE' in r.characteristics),
                  key=lambda r:(-(r.inclusion_rate or 0),-r.active_quantity,r.identity))
    orientation = {r.identity for r in core[:CORE_ORIENTATION_CAP]}
    # Overview mechanics: prioritize core evolution endpoints and their actual
    # active ancestors, not opaque functional-ID order among all Pokemon.
    # No archetype-name matching or inferred strategic role is involved.
    overview_rank = {}
    if 'DECK_OVERVIEW' in categories and not comparison:
        core_ids = {r.identity for r in core}
        def lineage(identity, seen=frozenset()):
            if identity in seen: return ()
            card = by_id[identity]
            return (identity, *(ancestor for parent in card.evolution_parents
                if parent in by_id and by_id[parent].quantity
                for ancestor in lineage(parent, seen | {identity})))
        endpoints = [c for c in profile.cards if c.quantity and c.category=='Pokemon'
            and c.identity in core_ids and c.evolution_parents]
        endpoints.sort(key=lambda c:(-len(set(lineage(c.identity))),
            -sum(by_id[i].quantity for i in set(lineage(c.identity))),c.identity))
        for endpoint in endpoints:
            for identity in lineage(endpoint.identity):
                if identity not in overview_rank: overview_rank[identity]=len(overview_rank)
    omissions = Counter()
    for row in profile.comparisons:
        card = by_id[row.identity]; labels = set(row.characteristics); referenced = row.identity in intent.card_references
        if 'CARD_QUANTITY' in categories and intent.card_references and not referenced:
            omissions['intent/card']+=1
            continue
        priority = 30
        if referenced: priority = 0
        elif comparison:
            if 'ABSENT_CARDS' in categories and 'COMMON_ABSENT' in labels: priority = 1-(row.inclusion_rate or 0)
            elif 'UNCOMMON_PRESENT' in labels: priority = 2+(row.inclusion_rate or 0)
            elif 'COMMON_ABSENT' in labels: priority = 4-(row.inclusion_rate or 0)
            elif labels & {'ABOVE_TYPICAL_QUANTITY','BELOW_TYPICAL_QUANTITY'}: priority = 5
            elif 'ARCHETYPE_CORE' in labels:
                if row.identity in orientation: priority = 6
                else:
                    omissions['rank/core-orientation']+=1
                    continue
        elif card.quantity:
            priority = {'Pokemon':2,'Energy':4,'Trainer':7}.get(card.category,9)
            if card.identity in overview_rank:
                priority = 1 + overview_rank[card.identity] / (len(overview_rank)+1)
        if priority == 30:
            omissions['intent/card']+=1
            continue
        if card.quantity and not comparison:
            add(priority,'composition','DERIVED_FACT',card.identity,dict(identity=card.identity,name=card.name,
                quantity=card.quantity,category=card.category,energy_type=card.energy_type,ace_spec=card.ace_spec,
                evolves_from=card.evolves_from,evolution_parents=card.evolution_parents),[deck_ref.id,card.reference.id])
        if comparison or referenced:
            data = row.model_dump(exclude={'characteristics'})
            add(priority,'comparison','EMPIRICAL_EVIDENCE',card.identity,data,[deck_ref.id,pop_ref.id])
            if labels: add(priority+0.1,'deviation','DERIVED_FACT',card.identity,dict(characteristics=row.characteristics,
                configuration=configuration()),[deck_ref.id,pop_ref.id])
        add(priority+0.2 if not comparison else priority+8,'mechanics','SOURCE_FACT',card.identity,
            dict(name=card.name,printed=[f.model_dump() for f in card.printed]),[card.reference.id])
    caps = dict(CAPS)
    if categories == {'UNKNOWN'}: caps = {k:min(v,2) for k,v in caps.items()}
    kept = []; counts = Counter()
    def assemble(items):
        used = {r for item in items for r in item.references}; size = 0
        for _ in range(12):
            value = Packet(profile_hash=profile.content_hash,question=question,intent=intent,evidence=tuple(items),
                references=tuple(references[r] for r in sorted(used)),serialized_bytes=size,content_hash='0'*64,
                coverage=Coverage(requested=intent.categories,included=tuple(sorted({i.kind for i in items})),
                    omitted=tuple(f'{k}:{v}' for k,v in sorted(omissions.items())),unavailable=profile.unavailable))
            value=value.model_copy(update={'content_hash':digest(value.model_dump(mode='json',exclude={'content_hash'}))})
            actual=len(canonical(value).encode())
            if actual==size: return value
            size=actual
        raise ValueError('Packet size did not stabilize')
    for _,_,_,item in sorted(candidates,key=lambda v:v[:3]):
        if item.kind=='deviation' and not any(i.kind=='comparison' and i.identity==item.identity for i in kept):
            omissions['dependency/deviation']+=1
            continue
        if counts[item.kind] >= caps.get(item.kind,1): omissions['cap/'+item.kind]+=1; continue
        if len(canonical(assemble([*kept,item])).encode()) > EVIDENCE_BYTES-512:
            omissions['budget/'+item.kind]+=1; continue
        kept.append(item);counts[item.kind]+=1
    result=assemble(kept)
    if result.serialized_bytes>EVIDENCE_BYTES or not {'deck','population'} <= set(result.coverage.included):
        raise ValueError('Mandatory evidence exceeds budget')
    return result
