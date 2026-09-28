"""Frozen real Standard snapshot; every test runs with network prohibited."""
from dataclasses import replace
import gzip
import json
from pathlib import Path
import socket

import pytest

from pokelab.alternative_retrieval import RetrievalIndex, parse_query, INTENTS
from pokelab.mechanics_discovery import Effect, Atom, Span

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a,**kw): raise AssertionError('Network prohibited')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket.socket,'connect_ex',forbidden)


@pytest.fixture(scope='module')
def index():
    directory=ROOT/'docs/phase-7c3-mechanics'
    cards=json.loads(gzip.decompress((directory/'cards.json.gz').read_bytes()))
    effects=[]
    for line in gzip.decompress((directory/'effects.jsonl.gz').read_bytes()).decode().splitlines():
        obj=json.loads(line)
        obj['atoms']=tuple(Atom(**{**a,'span':Span(**a['span']) if a['span'] else None}) for a in obj['atoms'])
        obj['unmatched_spans']=tuple(Span(**s) for s in obj['unmatched_spans'])
        effects.append(Effect(**obj))
    return RetrievalIndex(cards,effects)


def fid(index,printing):
    return next(c['functional_identity'] for c in index.cards if c['printing']==printing)


@pytest.mark.parametrize('query,printing',[
    ('Stop players from using Tools','me02.5-261'),
    ('Move damage counters','me02.5-099'),
    ('What prevents Abilities?','sv05-078'),
    ('What cards can copy attacks?','me02.5-075'),
    ('Recover Pokémon from the discard pile','me01-173'),
    ('What else can search for a Supporter?','me02-027'),
])
def test_specific_known_targets(index,query,printing):
    result=index.search(query)
    assert fid(index,printing) in [r['functional_identity'] for r in result['results']]


def test_reference_never_overrides_explicit_tools(index):
    result=index.search('Is there another card that stops players from using Tools?',fid(index,'me02.5-016'))
    assert result['query']['concepts']==['tool_nullification']
    assert not result['query']['reference_used']
    assert result['results'][0]['name']=='Jamming Tower'
    assert 'item_lock' not in result['results'][0]['components'][0]['matched_concepts']


def test_reference_similar_keeps_mechanical_and_functional_distinct(index):
    result=index.search('What cards perform a similar role to Budew?',fid(index,'me02.5-016'),50)
    assert result['query']['reference_used']
    assert {r['classification'] for r in result['results']} >= {'direct_mechanical','related_functional'}
    assert fid(index,'me02.5-016') not in [r['functional_identity'] for r in result['results']]


@pytest.mark.parametrize('query,opposite', [('mill my opponent','your deck'),('mill me',"opponent's deck")])
def test_direction_separation(index,query,opposite):
    results=index.search(query)['results']
    assert results
    for r in results:
        best=r['components'][0]
        assert best['classification']=='direct_mechanical'
        expected='opponent_mill' if opposite=='your deck' else 'self_mill'
        assert best['matched_relationships']==[expected]
        # A conditional trigger may mention the other deck; that is not the
        # direct discard action's target (e.g. retaliatory opponent mill).


@pytest.mark.parametrize('a,b',[
    ('mill my opponent','make my opponent run out of cards'),
    ('mill me','discard cards from the top of my own deck'),
    ('recover Pokémon from discard pile','get Pokémon back out of my discard pile'),
    ('move damage counters','transfer existing damage counters between Pokémon'),
    ('energy denial','take away Energy from my opponent\'s Pokémon'),
    ('item lock','stop players from using Items'),
    ('tool effect suppression','stop players from using Tools'),
    ('ability lock','stop Pokémon from using Abilities'),
])
def test_bounded_aliases(index,a,b):
    assert parse_query(a)['concepts']==parse_query(b)['concepts']
    aa={r['functional_identity'] for r in index.search(a)['results']}
    bb={r['functional_identity'] for r in index.search(b)['results']}
    assert len(aa&bb)/len(aa|bb)>=0.8


def test_constraints(index):
    basic=index.search('Are there other Basic Pokémon that can disrupt Items?')
    assert basic['results']
    assert all(r['category']=='Pokemon' and r['source_fields']['stage']=='Basic' for r in basic['results'])
    trainers=index.search('What Trainer cards recover Pokémon from discard pile?')
    assert trainers['results'] and all(r['category']=='Trainer' for r in trainers['results'])
    excluded=index.search('Recover Pokémon from discard pile excluding trainers')
    assert all(r['category']!='Trainer' for r in excluded['results'])
    assert index.search('Pokémon with 999 HP that draw cards')['status']=='partial'


@pytest.mark.parametrize('query',['Quantum banana transposition','What is best?','Move cards to the Lost Zone'])
def test_empty(index,query):
    assert index.search(query)['results']==[]


def test_taxonomy_absence_and_partial_are_not_gates(index):
    e=next(e for e in index.effects if e.printing=='me04-070' and e.component=='ability')
    assert not e.mechanics and not e.atoms
    result=index.search(e.raw_text)
    target=next(r for r in result['results'] if r['functional_identity']==e.functional_identity)
    assert target['classification']=='text_only_uncertain'
    assert target['components'][0]['exact_phrase']
    # Remove labels and atoms from an actual partly represented component: text
    # remains independently eligible. No synthetic claim of corpus coverage.
    m=next(e for e in index.effects if e.printing=='me02.5-099' and e.component=='ability')
    bare=replace(m,atoms=(),mechanics=())
    sub=RetrievalIndex(index.groups[m.functional_identity],[bare])
    assert sub.search(m.raw_text)['results'][0]['functional_identity']==m.functional_identity


def test_reprints_do_not_multiply_scores(index):
    a=index.search('Item lock')
    duplicate=RetrievalIndex(index.cards,index.effects+index.effects)
    b=duplicate.search('Item lock')
    assert [(r['functional_identity'],r['score']) for r in a['results']]==[(r['functional_identity'],r['score']) for r in b['results']]
    assert len({r['functional_identity'] for r in a['results']})==len(a['results'])
    assert len(next(r for r in a['results'] if r['name']=='Budew')['legal_printings'])>1


def test_full_text_universe_and_provenance(index):
    assert len(index.cards)==3345 and len(index.groups)==2092 and len(index.effects)==5180
    text=[e for e in index.effects if e.normalized_text]
    assert len({e.functional_identity for e in text})==1750
    assert sum(not e.mechanics for e in text)==88
    assert all(e.source_url and e.source_card_hash and e.checked_at for e in text)
    assert all(e in index.by_identity[e.functional_identity] for e in text)


@pytest.mark.parametrize('limit',[0,51,True,-1])
def test_invalid_bounds(index,limit):
    with pytest.raises(ValueError): index.search('draw cards',limit=limit)


def test_determinism_and_bounds(index):
    assert index.search('draw cards',limit=3)==index.search('draw cards',limit=3)
    assert len(index.search('draw cards',limit=3)['results'])==3
    with pytest.raises(ValueError): index.search('draw',reference='unknown')


def test_no_ownership_or_popularity_inputs(index):
    assert 'ownership' not in index.__dict__ and 'competitive' not in index.__dict__
    source=(ROOT/'src/pokelab/alternative_retrieval.py').read_text(encoding='utf-8')
    assert 'from .providers' not in source and 'from .collection' not in source


def test_atom_channel_is_independent(index):
    e=next(e for e in index.effects if e.printing=='me01-003' and e.component=='attack')
    # Architectural synthetic ablation, not a real-corpus retrieval claim.
    bare=replace(e,normalized_text='',raw_text=None,mechanics=())
    result=RetrievalIndex(index.groups[e.functional_identity],[bare]).search('heal damage')
    assert result['results'][0]['components'][0]['eligibility_channels']==['atoms']


def test_missing_property_is_disclosed_not_assumed(index):
    result=index.search('Draw cards without pokémon ex')
    assert result['status']=='partial'
    assert any(r['constraints_unevaluable'] for r in result['results'])
    assert all(r['source_fields'].get('suffix')!='ex' for r in result['results'])


def test_constraints_can_eliminate_all_candidates(index):
    result=index.search('Stage 2 Pokémon that stop players from using Tools')
    assert result['results']==[]
    assert result['query']['constraints']


def test_taxonomy_only_is_uncertain_not_direct(index):
    # Real Pass 1 lexical spread label on damage FOR each Energy, not damage TO each Pokémon.
    result=index.search('Spread damage to all Pokémon',limit=50)
    e=next(e for e in index.effects if e.printing=='me01-034' and e.component_index==0)
    sub=RetrievalIndex(index.groups[e.functional_identity],[e]).search('spread')
    assert sub['results'][0]['classification']=='text_only_uncertain'
    assert not sub['results'][0]['components'][0]['matched_relationships']
