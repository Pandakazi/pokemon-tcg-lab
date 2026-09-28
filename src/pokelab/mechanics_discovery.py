"""Offline discovery representation, not a rules executor or retrieval service.

Every component survives independently of atom/taxonomy coverage. Text spans are
lexical evidence, never a claim of fully resolved effect scope or game legality.
No collection, competitive, workspace, provider or API dependencies.
"""
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

from .engine import functional_signature

VERSION = 'pokelab-mechanics-discovery-v1'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().replace('’', "'").split())


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Atom:
    action: str
    order: int
    span: Span | None
    source_field: str
    object: str | None = None
    quantity: str | None = None
    affected_player: str | None = None
    source_zone: str | None = None
    destination_zone: str | None = None
    optionality: str = 'unknown'
    polarity: str = 'unknown'
    scope_status: str = 'lexical_only'
    context: str = ''
    previous_atom: int | None = None
    relationship: str = 'text_order_not_execution'


@dataclass(frozen=True)
class Effect:
    id: str
    printing: str
    functional_identity: str
    name: str
    category: str
    component: str
    component_index: int
    component_name: str | None
    source_url: str
    source_card_hash: str
    checked_at: str
    raw_text: str | None
    normalized_text: str
    structured_json: str
    atoms: tuple[Atom, ...]
    mechanics: tuple[str, ...]
    unmatched_spans: tuple[Span, ...]
    ambiguities: tuple[str, ...]
    source_issues: tuple[str, ...]
    representation: str


# Verb families observed across the inspected English corpus. These are not a
# gate on component retention: unknown text is emitted with unmatched spans.
ACTION_PATTERNS = (
    ('usage_limit', r"\b(?:can't|cannot) use more than\b"),
    ('restrict', r"\b(?:can't|cannot|don't|doesn't) (?:play|use|attack|retreat|evolve|recover|take|attach)\b"),
    ('disable', r'\b(?:has|have) no abilities\b|\blose all abilities\b'),
    ('draw', r'\bdraws?\b'), ('search', r'\bsearch\b'),
    ('discard', r'\bdiscards?\b(?! pile)'), ('move', r'\bmove\b'),
    ('attach', r'\battach\b'), ('shuffle', r'\bshuffles?\b'),
    ('switch', r'\bswitch\b'), ('heal', r'\bheal\b'),
    ('prevent', r'\bprevent\b'), ('devolve', r'\bdevolve\b'),
    ('evolve', r'\bevolve\b'), ('reveal', r'\breveal\b'),
    ('inspect', r'\blook at\b'), ('choose', r'\bchooses?\b'),
    ('place', r'\bplace\b'), ('put', r'\bput\b'),
    ('recover', r'\brecovers? from\b'), ('remove', r'\bremove\b'),
    ('coin_flip', r'\bflip\b'), ('knock_out', r'\bknock out\b'),
    ('copy', r'\buse\b[^.;]{0,160}\b(?:as (?:the effect of )?this attack)\b'),
    ('damage_modifier', r'\b(?:does|do|takes?|take)\b[^.;]{0,60}\b(?:more|less) damage\b'),
    ('damage', r'\b(?:does|do) \d+ damage\b'),
    ('special_condition', r'\b(?:is|are) now (?:poisoned|burned|confused|paralyzed|asleep)\b'),
    ('retreat_modifier', r'\b(?:retreat cost|no retreat cost)\b'),
    ('change', r'\b(?:change|becomes?)\b'), ('prize_take', r'\btake\b[^.;]{0,50}\bprize\b'),
    ('reorder', r'\b(?:any order|rearrange)\b'),
    ('provide_energy', r'\bprovides\b'),
    ('counter_scale', r'\bdouble the number of damage counters\b'),
    ('prize_modifier', r'\btakes? \d+ fewer prize cards?\b'),
    ('weakness_change', r'\bweakness\b[^.;]{0,90}\bis now\b'),
    ('type_change', r'\bit is (?:\{[a-z]\}(?: and )?)+ type\b'),
    ('hp_modifier', r'\bgets [+-]\d+ hp\b'),
    ('bench_capacity', r'\b(?:can|may) have up to \d+ pokémon on (?:their|your) bench\b'),
    ('attack_cost_modifier', r'\bcost \{[a-z]\} (?:less|more)\b'),
    ('tool_nullification', r'\bpokémon tools\b[^.;]{0,120}\bhave no effect\b'),
)


def span(text, start, end):
    return Span(start, end, text[start:end])


def atomize(text, structured):
    matches = []
    for priority, (action, pattern) in enumerate(ACTION_PATTERNS):
        for match in re.finditer(pattern, text):
            matches.append((match.start(), priority, match.end(), action))
    chosen = []
    for start, _, end, action in sorted(matches):
        if any(start < old_end and end > old_start for old_start, old_end, _ in chosen): continue
        if action=='disable' and re.search(r'\bcard that\s*$',text[:start]): continue
        chosen.append((start, end, action))
    atoms = []
    for index, (start, end, action) in enumerate(chosen):
        sentence_end = re.search(r'[.;!?](?:\s|$)', text[end:])
        stop = end + sentence_end.start() + 1 if sentence_end else len(text)
        if index+1 < len(chosen): stop = min(stop, chosen[index+1][0])
        fragment = text[start:stop].strip()
        stop = start + len(fragment)
        prefix_start = max(text.rfind('.', 0, start), text.rfind(';', 0, start))+1
        context = text[prefix_start:start].strip()
        obj = re.search(r'\b(?:damage counters?|(?:basic |special )?energy(?: cards?)?|supporter(?: cards?)?|item(?: cards?)?|pokémon tools?|stadium(?: cards?)?|prize cards?|(?:basic |evolution |benched |active )?pokémon|cards?|damage|attacks?|abilities)\b',fragment)
        qty = re.match(r'\w+\s+((?:up to )?\d+|all|a|an|any number of)\b',fragment)
        # Only direct from/to phrases; pronouns are never resolved here.
        source = re.search(r"\bfrom (?:the |your |your opponent's )?(discard pile|hand|deck|bench|active spot|lost zone|prize cards)\b",fragment)
        dest = re.search(r"\b(?:into|onto|to) (?:the |your |your opponent's )?(discard pile|hand|deck|bench|active spot|lost zone|prize cards)\b",fragment)
        target = re.search(r"\b(?:from|to|into|onto) (your opponent's|your)\b",fragment)
        optional = 'may' if re.search(r'\bmay\s*$',context) else 'unknown'
        atoms.append(Atom(action,index,span(text,start,stop),'effect',obj.group() if obj else None,
            qty.group(1) if qty else None,target.group(1) if target else None,
            source.group(1) if source else None,dest.group(1) if dest else None,
            optional,context=context,previous_atom=index-1 if index else None))
    if 'damage' in structured and type(structured['damage']) in (int,str):
        atoms.append(Atom('printed_damage',len(atoms),None,'damage',object='damage',
            quantity=str(structured['damage']),scope_status='explicit_source_field'))
    # Unmatched spans measure lexical extraction only, not semantic completeness.
    uncovered=[];cursor=0
    for atom in atoms:
        if atom.span is None: continue
        if text[cursor:atom.span.start].strip(' ,.;'): uncovered.append(span(text,cursor,atom.span.start))
        cursor=atom.span.end
    if text[cursor:].strip(' ,.;'): uncovered.append(span(text,cursor,len(text)))
    return tuple(atoms),tuple(uncovered)


def load_taxonomy():
    return json.loads(Path(__file__).with_name('mechanics_taxonomy.json').read_text(encoding='utf-8'))


def represent(card, component, index, data, checked_at, taxonomy=None):
    taxonomy = taxonomy or load_taxonomy()
    issues=[]
    if 'invalid_field' in data or 'invalid_component' in data: issues.append('component_wrong_type')
    raw=data.get('effect')
    if raw is not None and not isinstance(raw,str): issues.append('effect_wrong_type');raw=None
    text=normalize(raw) if isinstance(raw,str) else ''
    if not text: issues.append('effect_text_not_supplied')
    if component=='attack':
        if 'cost' not in data: issues.append('attack_cost_not_supplied')
        elif not isinstance(data['cost'],list): issues.append('attack_cost_wrong_type')
        if 'damage' not in data: issues.append('attack_damage_not_supplied')
    atoms,unmatched=atomize(text,data)
    mechanics=set()
    for rule in taxonomy['concepts']:
        for atom in atoms:
            if atom.action in rule['actions'] and (rule['pattern'] is None or
                (atom.span and re.search(rule['pattern'],atom.span.text))):
                mechanics.add(rule['id']);break
    ambiguous=[]
    if re.search(r'\b(if|when|whenever|unless|as long as|during|before|after)\b',text): ambiguous.append('condition_or_timing_scope_unresolved')
    if re.search(r'\b(it|them|those|that|this way)\b',text): ambiguous.append('reference_resolution_unresolved')
    if re.search(r'\b(or|choose|may|flip|for each|until)\b',text): ambiguous.append('choice_quantity_or_option_scope_unresolved')
    if len(atoms)>1: ambiguous.append('compound_scope_not_executed')
    # Only this very small grammar claims complete representation. All other
    # matched effects remain partial, even if every word lies inside a span.
    simple = bool(re.fullmatch(r'draw \d+ cards?\.?',text)) or (not text and len(atoms)==1 and atoms[0].action=='printed_damage' and str(data['damage']).isdigit())
    status='represented_simple' if simple else 'partial' if atoms else 'unclassified' if text else 'missing'
    fid=hashlib.sha256(functional_signature(card).encode()).hexdigest()[:32]
    source_hash=digest(card)
    key=dict(printing=card['id'],component=component,index=index,field=data.get('field','effect'),source_hash=source_hash,version=VERSION)
    return Effect(digest(key),card['id'],fid,card['name'],card['category'],component,index,
        data.get('name'),f"https://api.tcgdex.net/v2/en/cards/{card['id']}",source_hash,checked_at,
        raw,text,canonical(data),atoms,tuple(sorted(mechanics)),unmatched,tuple(ambiguous),tuple(issues),status)


def components(card):
    for kind,key in (('attack','attacks'),('ability','abilities')):
        if key in card and not isinstance(card[key],list):
            yield 'other',0,dict(effect=None,invalid_field=key,original=card[key])
        else:
            for index,item in enumerate(card.get(key,[])):
                yield kind,index,item if isinstance(item,dict) else dict(effect=None,invalid_component=item)
    if card.get('category') in ('Trainer','Energy') or 'effect' in card:
        yield 'energy_effect' if card['category']=='Energy' else 'trainer_effect' if card['category']=='Trainer' else 'other',0,dict(effect=card.get('effect'))
    rules=card.get('rules')
    if isinstance(rules,str): yield 'other',0,dict(effect=rules,field='rules')
    elif isinstance(rules,list):
        for index,rule in enumerate(rules): yield 'other',index,dict(effect=rule,field='rules')


def analyze(database):
    """Read-only explicit SQLite snapshot. Never initialize or repair source DB."""
    path=Path(database).resolve()
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        if db.execute('PRAGMA user_version').fetchone()[0]!=1: raise ValueError('Unsupported card schema')
        rows=list(db.execute('SELECT id,category,game,standard,regulation,raw,checked_at,fetched_at FROM cards ORDER BY id'))
        sync=db.execute("SELECT value FROM metadata WHERE key='last_sync'").fetchone()
    taxonomy=load_taxonomy();effects=[];cards=[];failures=[];exclusions=Counter()
    for row in rows:
        if row['game']!='tcg' or row['standard']!=1:
            exclusions[f"{row['game']}:standard={row['standard']}"]+=1;continue
        try:
            raw=json.loads(row['raw'])
            if not isinstance(raw,dict) or not isinstance(raw.get('name'),str) or raw.get('id')!=row['id']: raise ValueError('card shape')
            if raw.get('legal',{}).get('standard') is not True:
                exclusions['indexed_raw_legality_disagreement']+=1;continue
            if raw.get('language') not in (None,'en','English'):
                exclusions['explicit_non_english']+=1;continue
            fid=hashlib.sha256(functional_signature(raw).encode()).hexdigest()[:32]
            card_effects=[represent(raw,kind,index,item,row['checked_at'],taxonomy) for kind,index,item in components(raw)]
            effects.extend(card_effects)
            cards.append(dict(printing=row['id'],name=raw['name'],category=raw['category'],functional_identity=fid,
                regulation=raw.get('regulationMark'),standard=True,checked_at=row['checked_at'],fetched_at=row['fetched_at'],
                language_explicit=raw.get('language'),source_hash=digest(raw),component_count=len(card_effects),
                source_fields={k:raw[k] for k in ('stage','types','hp','evolveFrom','suffix','trainerType','energyType') if k in raw}))
        except (ValueError,KeyError,TypeError,AttributeError):
            failures.append(dict(printing=row['id'],reason='invalid_source_record'))
    def coverage(items):
        usable=[e for e in items if e.normalized_text or any(a.action=='printed_damage' for a in e.atoms)]
        represented=sum(bool(e.atoms) for e in usable);mapped=sum(bool(e.mechanics) for e in usable)
        return dict(components=len(items),usable=len(usable),text_bearing=sum(bool(e.normalized_text) for e in items),
            atom_represented=represented,atom_percent=round(100*represented/len(usable),2) if usable else 0,
            text_action_represented=sum(any(a.source_field=='effect' for a in e.atoms) for e in items if e.normalized_text),
            taxonomy_mapped=mapped,taxonomy_percent=round(100*mapped/len(usable),2) if usable else 0,
            partial=sum(e.representation=='partial' for e in usable),unclassified=sum(e.representation=='unclassified' for e in usable),
            taxonomy_unclassified=sum(not e.mechanics for e in usable),simple=sum(e.representation=='represented_simple' for e in usable),
            ambiguous=sum(bool(e.ambiguities) for e in usable),missing=sum(e.representation=='missing' for e in items),
            source_issue_components=sum(bool(e.source_issues) for e in items))
    frequencies=Counter(label for e in effects for label in e.mechanics)
    examples={label:sorted({e.printing for e in effects if label in e.mechanics})[:5] for label in sorted(frequencies)}
    text_audit={key:dict(effect_count=sum(bool(re.search(pattern,e.normalized_text)) for e in effects),
        example_printings=sorted({e.printing for e in effects if re.search(pattern,e.normalized_text)})[:5],
        interpretation='text occurrence only, not a classified mechanic')
        for key,pattern in taxonomy.get('additional_text_audit',{}).items()}
    sequences={}
    for e in effects:
        key=' > '.join(a.action for a in e.atoms)
        if key: sequences.setdefault(key,[]).append(e)
    rare_sequences=[dict(sequence=key,functional_identities=len({e.functional_identity for e in items}),
        printings=sorted({e.printing for e in items})) for key,items in sorted(sequences.items())
        if len({e.functional_identity for e in items})<=2]
    snapshot=dict(version=VERSION,total_cache_rows=len(rows),selected_printings=len(cards),functional_identities=len({c['functional_identity'] for c in cards}),
        category_counts=dict(sorted(Counter(c['category'] for c in cards).items())),
        regulation_counts=dict(sorted(Counter(str(c['regulation']) for c in cards).items())),
        last_sync=json.loads(sync[0]) if sync else None,source_failures=failures,exclusions=dict(exclusions),
        checked_at_range=[min((c['checked_at'] for c in cards),default=None),max((c['checked_at'] for c in cards),default=None)],
        corpus_hash=digest(cards),taxonomy_hash=digest(taxonomy),coverage=coverage(effects),
        coverage_by_component={kind:coverage([e for e in effects if e.component==kind]) for kind in sorted({e.component for e in effects})},
        cards_with_text=len({e.printing for e in effects if e.normalized_text}),
        cards_with_source_issues=len({e.printing for e in effects if e.source_issues}),
        unique_normalized_texts=len({e.normalized_text for e in effects if e.normalized_text}),
        duplicate_effect_ids=len(effects)-len({e.id for e in effects}),
        text_audit=text_audit,rare_atom_sequences=rare_sequences,
        taxonomy_frequencies=dict(sorted(frequencies.items())),taxonomy_examples=examples,
        unobserved_concepts=[r['id'] for r in taxonomy['concepts'] if r['id'] not in frequencies],
        source_issue_counts=dict(sorted(Counter(i for e in effects for i in e.source_issues).items())))
    return snapshot,cards,effects,taxonomy
