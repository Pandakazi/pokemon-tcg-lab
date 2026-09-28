"""Bounded offline lexical retrieval; never strategic or rules equivalence.

The index is the complete Pass 1 snapshot, not the taxonomy's classified subset.
Scores are maxima over components/printings, never sums over reprints. All source
components supporting a result survive for inspection. No workspace/provider I/O.
"""
from collections import defaultdict
from dataclasses import asdict, dataclass
import re

from .mechanics_discovery import analyze, normalize

VERSION = 'pokelab-alternative-retrieval-v1'
DEFAULT_LIMIT = 10
MAX_LIMIT = 50


@dataclass(frozen=True)
class Intent:
    concept: str
    query: str
    actions: tuple[str, ...]
    evidence: str
    object: str = ''
    player: str = ''
    source: str = ''
    destination: str = ''


# Deliberately bounded paraphrases. Evidence patterns refer to a single component;
# they do not resolve arbitrary pronouns, conditions or execution legality.
INTENTS = (
    Intent('opponent_mill', r'mill (?:my |the )?opponent|opponent.*run out of cards|discard.*top.*opponent.*deck', ('discard',), r'discard[^.;]*top[^.;]*opponent\'s deck', 'cards', 'opponent', 'deck', 'discard pile'),
    Intent('self_mill', r'mill (?:me|myself)|self.mill|discard.*top.*(?:my|own) deck', ('discard',), r'discard[^.;]*top[^.;]*your deck', 'cards', 'self', 'deck', 'discard pile'),
    Intent('pokemon_recovery', r'(?:recover|get).*pokémon.*(?:discard|back)|get pokémon back', ('put','shuffle'), r'(?:put|shuffle)[^.;]*pokémon[^.;]*discard pile', 'pokémon', 'self', 'discard pile'),
    Intent('energy_recovery', r'(?:recover|retrieve).*energy|energy recovery', ('put','shuffle'), r'(?:put|shuffle)[^.;]*energy[^.;]*discard pile', 'energy', 'self', 'discard pile'),
    Intent('energy_denial', r'energy (?:denial|removal)|(?:discard|remove|take away).*energy.*opponent|take away.*opponent.*energy', ('discard','remove'), r'(?:discard|remove)[^.;]*energy[^.;]*opponent', 'energy', 'opponent'),
    Intent('energy_acceleration', r'energy accelerat|attach.*energy', ('attach',), r'attach[^.;]*energy', 'energy'),
    Intent('damage_counter_movement', r'move damage counters|transfer.*(?:existing damage|damage counters)|moving existing damage', ('move',), r'move[^.;]*damage counters', 'damage counters'),
    Intent('damage_counter_placement', r'(?:place|put).*damage counters|counter placement', ('put','place'), r'(?:put|place)[^.;]*damage counters', 'damage counters'),
    Intent('tool_nullification', r'tool.*(?:suppression|no effect)|(?:stop|suppress|disable).*tools|using tools', ('tool_nullification','restrict'), r'pokémon tools[^.;]*have no effect|(?:can\'t|cannot)[^.;]*(?:play|use)[^.;]*tool', 'tool'),
    Intent('tool_removal', r'(?:discard|remove).*tools|tool removal', ('discard','remove'), r'(?:discard|remove)[^.;]*pokémon tools?', 'tool'),
    Intent('item_lock', r'item.*(?:lock|restriction)|(?:disrupt|stop|prevent).*items|using items', ('restrict',), r'(?:can\'t|cannot) (?:play|use)[^.;]*item cards', 'item'),
    Intent('ability_lock', r'ability (?:lock|restriction)|(?:prevent|stop|suppress|disable).*abilit|using abilities', ('disable',), r'(?:has|have) no abilities|lose all abilities', 'abilities'),
    Intent('supporter_search', r'search.*supporter|find.*supporter', ('search',), r'search[^.;]*supporter', 'supporter', '', 'deck'),
    Intent('pokemon_search', r'search.*pokémon|find.*pokémon', ('search',), r'search[^.;]*pokémon', 'pokémon', '', 'deck'),
    Intent('draw', r'\bdraw\b', ('draw',), r'\bdraw \d+ cards'),
    Intent('hand_disruption', r'hand disruption|discard.*opponent.*hand', ('discard','shuffle'), r'discard[^.;]*opponent\'s hand|opponent[^.;]*shuffle[^.;]*hand', 'cards', 'opponent', 'hand'),
    Intent('gust', r'\bgust\b|force.*switch|switch.*opponent', ('switch',), r'switch[^.;]*opponent[^.;]*(?:benched|bench|active)', 'pokémon', 'opponent'),
    Intent('retreat_lock', r'(?:prevent|stop).*retreat|retreat (?:lock|restriction)', ('restrict',), r'(?:can\'t|cannot) retreat'),
    Intent('stadium_removal', r'(?:discard|remove).*stadium|stadium removal', ('discard',), r'discard[^.;]*stadium', 'stadium'),
    Intent('healing', r'\bheal(?:ing)?\b', ('heal',), r'\bheal\b'),
    Intent('damage_prevention', r'prevent.*damage|damage prevention', ('prevent',), r'prevent all damage'),
    Intent('damage_reduction', r'reduce.*damage|damage reduction|take less damage', ('damage_modifier',), r'takes?[^.;]*less damage'),
    Intent('spread_damage', r'\bspread\b|damage.*all.*pokémon', ('damage',), r'does[^.;]*damage to each'),
    Intent('bench_damage', r'damage.*bench|bench damage', ('damage',), r'does[^.;]*damage to[^.;]*benched'),
    Intent('prize_reduction', r'prize reduction|fewer prizes|prize liability', ('prize_modifier','restrict'), r'fewer prize|can\'t take any prize'),
    Intent('prize_access', r'prize manipulation|take.*prize', ('prize_take',), r'take[^.;]*prize'),
    Intent('copy_effect', r'copy.*attack|attack copying', ('copy',), r'use[^.;]*as (?:the effect of )?this attack'),
    Intent('evolution_acceleration', r'evolution accelerat|evolve.*same turn', ('evolve','put'), r'(?:evolve|evolves)[\s\S]*(?:this turn)|(?:this turn)[^.]*evolve'),
    Intent('devolution', r'\bdevol', ('devolve',), r'\bdevolve\b'),
    Intent('poison', r'\bpoison', ('special_condition',), r'now poisoned'),
    Intent('weakness_change', r'change.*weakness|weakness manipulation', ('weakness_change',), r'weakness[^.;]*is now'),
    Intent('top_deck_placement', r'put.*top.*deck|top.deck placement', ('put',), r'put[^.;]*top of[^.;]*(?:deck|it)'),
    Intent('reorder', r'reorder|rearrange|deck order', ('reorder',), r'any order|rearrange'),
    Intent('rule_box_interaction', r'rule box', ('choose','discard','disable','search'), r'rule box'),
    Intent('pokemon_ex_interaction', r'interact.*pokémon ex|pokémon ex interaction', ('restrict','prize_modifier','damage_modifier'), r'pokémon ex'),
    Intent('lost_zone_movement', r'lost zone', ('put','move'), r'lost zone'),
)
BY_CONCEPT = {i.concept: i for i in INTENTS}
# Functionally related control, explicitly not equivalent mechanics.
RELATED = {'item_lock': {'tool_nullification','ability_lock'},
           'tool_nullification': {'tool_removal'}}
STOP = set('what which cards card can could other another are there that the a an of to from in my me own your opponent opponents pokemon pokémon deck with for and or does do is it this perform similar role else any please'.split())


def tokens(text):
    return set(re.findall(r"[\w]+", text)) - STOP


def atom_agrees(atom,intent):
    """Independent structured signal; missing scope is not invented agreement."""
    if atom.action not in intent.actions: return False
    # A generic verb alone cannot stand for a specialized concept such as Lost
    # Zone movement, Prize reduction or Weakness change.
    if not intent.object and intent.concept not in {'draw','healing','devolution','copy_effect','reorder'}: return False
    if intent.object and (not atom.object or intent.object.rstrip('s') not in atom.object): return False
    if intent.player:
        expected="your opponent's" if intent.player=='opponent' else 'your'
        if atom.affected_player!=expected: return False
    if intent.source and atom.source_zone!=intent.source: return False
    if intent.destination and atom.destination_zone!=intent.destination: return False
    return True


def parse_query(text, reference=None):
    if not isinstance(text,str) or not text.strip() or len(text)>1000:
        raise ValueError('Query must contain 1–1000 characters')
    normalized=normalize(text).replace('pokemon','pokémon')
    intents=[i for i in INTENTS if re.search(i.query,normalized)]
    constraints=[]
    patterns=(('category','Pokemon',r'(?:other |basic |stage [12] )pokémon|what pokémon'),
              ('category','Trainer',r'trainer cards|what trainers'),
              ('stage','Basic',r'\bbasic pokémon\b'),
              ('stage','Stage1',r'\bstage 1 pokémon\b'),
              ('stage','Stage2',r'\bstage 2 pokémon\b'),
              ('trainerType','Supporter',r'\bsupporter cards that\b'),
              ('trainerType','Item',r'\bitem cards that\b'),
              ('trainerType','Tool',r'\btool cards that\b'))
    for field,value,pattern in patterns:
        if re.search(pattern,normalized): constraints.append(dict(field=field,value=value,negative=False))
    for value in ('Grass','Fire','Water','Lightning','Psychic','Fighting','Darkness','Metal','Dragon','Colorless'):
        if re.search(r'\b'+value.lower()+r' pokémon\b',normalized):
            constraints.extend([dict(field='category',value='Pokemon',negative=False),dict(field='types',value=value,negative=False)])
    for word,field,value in (('trainers','category','Trainer'),('pokémon ex','suffix','ex')):
        if re.search(r'(?:no|exclude|excluding|without) '+word,normalized):
            constraints.append(dict(field=field,value=value,negative=True))
    unknown=[]
    if re.search(r'\b(?:resistance|retreat cost|attack cost|hp|owned|cheapest)\b',normalized):
        unknown.append('property_constraint_not_supported')
    return dict(text=text,normalized=normalized,concepts=[i.concept for i in intents],
        actions=sorted({a for i in intents for a in i.actions}),objects=sorted({i.object for i in intents if i.object}),
        players=sorted({i.player for i in intents if i.player}),source_zones=sorted({i.source for i in intents if i.source}),
        destination_zones=sorted({i.destination for i in intents if i.destination}),constraints=constraints,
        reference_functional_identity=reference,unresolved_text=normalized,
        recognized_phrases=[m.group() for i in intents for m in re.finditer(i.query,normalized)],
        limitations=unknown)


class RetrievalIndex:
    def __init__(self,cards,effects,corpus_hash=None):
        self.cards=sorted(cards,key=lambda c:c['printing'])
        self.effects=sorted(effects,key=lambda e:e.id)
        self.corpus_hash=corpus_hash
        self.groups=defaultdict(list)
        self.by_identity=defaultdict(list)
        for c in self.cards: self.groups[c['functional_identity']].append(c)
        for e in self.effects: self.by_identity[e.functional_identity].append(e)

    @classmethod
    def from_database(cls,path):
        summary,cards,effects,_=analyze(path)
        return cls(cards,effects,summary['corpus_hash'])

    def search(self,text,reference=None,limit=DEFAULT_LIMIT):
        if type(limit) is not int or not 1<=limit<=MAX_LIMIT: raise ValueError('Result limit must be 1–50')
        q=parse_query(text,reference)
        if reference and reference not in self.groups: raise ValueError('Unknown Standard reference identity')
        # User's explicit mechanic always wins over reference-card mechanics.
        if not q['concepts'] and reference and re.search(r'similar role|similar effect',q['normalized']):
            q['concepts']=sorted({m for e in self.by_identity[reference] for m in e.mechanics if m in BY_CONCEPT and m!='draw'})
            q['reference_used']=True
        else: q['reference_used']=False
        intents=[BY_CONCEPT[c] for c in q['concepts']]
        if q['reference_used']:
            q.update(actions=sorted({a for i in intents for a in i.actions}),
                objects=sorted({i.object for i in intents if i.object}),
                players=sorted({i.player for i in intents if i.player}),
                source_zones=sorted({i.source for i in intents if i.source}),
                destination_zones=sorted({i.destination for i in intents if i.destination}))
        requested=set(q['concepts'])
        related=set().union(*(RELATED.get(c,set()) for c in requested)) if requested else set()
        terms=tokens(q['normalized'])
        hits=defaultdict(list)
        for e in self.effects:
            words=tokens(e.normalized_text)
            overlap=sorted(terms & words)
            exact_phrase=bool(e.normalized_text and len(q['normalized'])>=12 and q['normalized'].rstrip('.?') in e.normalized_text)
            lexical=exact_phrase or (len(overlap)>=2 and len(overlap)/max(len(terms),1)>=0.5)
            mechanical=[i.concept for i in intents if re.search(i.evidence,e.normalized_text)]
            matching_atoms=[a for a in e.atoms if any(atom_agrees(a,i) or
                (a.action in i.actions and re.search(i.evidence,e.normalized_text)) for i in intents)]
            exact=sorted(requested & set(e.mechanics))
            near=sorted(related & set(e.mechanics))
            # Independent union: no taxonomy/atom requirement for text candidates.
            if not (lexical or matching_atoms or exact or near or mechanical): continue
            if reference==e.functional_identity: continue
            # Explicit direction is a hard constraint only for demonstrably opposite
            # mill effects. Unresolved text remains inspectable, never promoted.
            opposite='self_mill' if 'opponent_mill' in requested else 'opponent_mill' if 'self_mill' in requested else None
            if opposite and re.search(BY_CONCEPT[opposite].evidence,e.normalized_text) and not mechanical: continue
            signals=dict(relationship=100 if mechanical and matching_atoms else 0,
                atoms=8 if matching_atoms else 0,
                exact_phrase=110 if exact_phrase else 0,concept=25 if exact else 0,
                related_concept=12 if near else 0,text=min(20,len(overlap)*3) if lexical else 0,
                uncertainty=-3 if e.ambiguities or e.representation=='partial' else 0)
            # Full phrase on unclassified text intentionally outranks generic labels.
            classification='direct_mechanical' if mechanical and matching_atoms else 'related_functional' if near and not exact else 'text_only_uncertain'
            hits[e.functional_identity].append(dict(effect=asdict(e),classification=classification,
                score=sum(signals.values()),score_components=signals,matched_atoms=[asdict(a) for a in matching_atoms],
                matched_concepts=exact,related_concepts=near,matched_relationships=mechanical,
                matched_text=overlap if lexical else [],exact_phrase=exact_phrase,
                eligibility_channels=[name for name,yes in [('text',lexical or bool(mechanical)),('atoms',bool(matching_atoms)),('taxonomy',bool(exact or near))] if yes]))
        results=[]
        for fid,components in hits.items():
            legal=self.groups[fid]
            satisfied=[];unevaluable=[];eligible=[]
            for card in legal:
                failed=False;missing=[]
                for constraint in q['constraints']:
                    field=constraint['field'];wanted=constraint['value']
                    value=card.get(field,card['source_fields'].get(field))
                    if value is None: missing.append(constraint);continue
                    equal=wanted in value if isinstance(value,list) else normalize(str(value))==normalize(wanted)
                    if equal==constraint['negative']: failed=True;break
                if not failed: eligible.append((card,missing))
            if not eligible: continue
            representative,unevaluable=min(eligible,key=lambda pair:(len(pair[1]),pair[0]['printing']))
            satisfied=[c for c in q['constraints'] if c not in unevaluable]
            components.sort(key=lambda x:(-x['score'],x['effect']['id']))
            best=components[0]
            results.append(dict(functional_identity=fid,name=representative['name'],category=representative['category'],
                source_fields=representative['source_fields'],representative=representative,
                legal_printings=legal,classification=best['classification'],score=best['score'],
                score_components=best['score_components'],components=components,
                constraints_satisfied=satisfied,constraints_unevaluable=unevaluable))
        results.sort(key=lambda r:(-r['score'],normalize(r['name']),r['functional_identity']))
        return dict(version=VERSION,corpus_hash=self.corpus_hash,query=q,limit=limit,total_candidates=len(results),
            results=results[:limit],truncated=len(results)>limit,
            status='empty' if not results else 'partial' if q['limitations'] or any(r['constraints_unevaluable'] for r in results[:limit]) else 'candidates',
            limitations=['Lexical candidates are not strategic substitutes or verified executable rules.',
                'Conditions, pronouns and unresolved text require source inspection.']+q['limitations'])
