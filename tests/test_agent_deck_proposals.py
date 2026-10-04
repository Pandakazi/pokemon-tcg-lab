"""Synthetic card records, real read-only domain validation, no live providers."""
import json
import sqlite3
from copy import deepcopy
import httpx
import pytest
from tcg_lab.card_db import SQLiteCards
from pokelab import agent_conversation as c, agent_deck_proposals as d, agent_research as a
from pokelab.agent_providers import Selection
from pokelab.decks import deck_identity
from pokelab.collection import Collection
from pokelab.agent_context_sources import SnapshotCards
from test_card_pool_research import sources, setup, research, offline


@pytest.fixture
def stores(sources):
    records=[
      dict(id='qa-pikachu',name='Pikachu ex',category='Pokemon',stage='Basic',suffix='ex',attacks=[dict(name='Spark',cost=['Lightning'],damage=20)]),
      dict(id='qa-munkidori',name='Munkidori',category='Pokemon',stage='Basic',abilities=[dict(name='Adrena-Brain',effect='As long as this Pokémon has any Darkness Energy attached, you may move damage counters.')]),
      dict(id='qa-draw',name='Draw Helper',category='Pokemon',stage='Basic',abilities=[dict(name='Draw',effect='Draw 2 cards.')]),
      dict(id='qa-recover',name='Recovery Tool',category='Trainer',trainerType='Item',effect='Put 2 Pokémon from your discard pile into your hand.'),
      dict(id='qa-old',name='Old Recovery',category='Trainer',trainerType='Item',effect='Put 2 Pokémon from your discard pile into your hand.',legal={'standard':False}),
      dict(id='qa-ace1',name='ACE Draw',category='Trainer',trainerType='Item',rarity='ACE SPEC',effect='Draw 2 cards.'),
      dict(id='qa-ace2',name='ACE Recovery',category='Trainer',trainerType='Item',rarity='ACE SPEC',effect='Put 2 Pokémon from your discard pile into your hand.'),
      dict(id='qa-energy',name='Lightning Energy',category='Energy',energyType='Normal',types=['Lightning']),
      dict(id='qa-dark',name='Darkness Energy',category='Energy',energyType='Normal',types=['Darkness']),
      dict(id='qa-evolution',name='Evolved Helper',category='Pokemon',stage='Stage1',evolveFrom='Missing Basic',attacks=[dict(name='Big',cost=['Fire']*4,damage=100)]),
      dict(id='qa-alakazam1',name='Alakazam',category='Pokemon',stage='Stage2',abilities=[dict(name='First',effect='Draw 2 cards.')]),
      dict(id='qa-alakazam2',name='Alakazam',category='Pokemon',stage='Stage2',abilities=[dict(name='Second',effect='Heal 20 damage.')]),
    ]
    db=SQLiteCards(sources.paths['cards'])
    for card in records:
        value=dict(rarity='Common',legal={'standard':True},variants={'normal':True},set={'id':'qa'},localId=card['id'],**{k:v for k,v in card.items() if k not in ('rarity','legal')})
        value.update({k:card[k] for k in ('rarity','legal') if k in card});db.put(value)
    with sqlite3.connect(sources.paths['cards']) as connection:
        connection.execute("UPDATE cards SET game='tcg' WHERE id LIKE 'qa-%'")
    return sources


def row(printing,quantity,role=''):return dict(printing_id=printing,quantity=quantity,role=role)
def list_proposal(cards):return dict(kind='list',name='Weird Pikachu',cards=cards,rationale='Preserve the unusual concept and test the support engine.')
def legal():return [row('qa-pikachu',4),row('qa-munkidori',2),row('qa-draw',4),row('qa-recover',4),row('qa-energy',46)]


def service(stores,proposal=None,premises=(),text='I would keep the concept and test the support engine.',hook=None):
    calls=[]
    def handle(req):
        body=json.loads(req.content);calls.append(body)
        assert body['provider']=={'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0,'request':0}}
        assert body['max_tokens']==4096 and 'authorization' not in req.headers
        if hook:hook()
        value=dict(version='pokelab-conversation-answer-v1',paragraphs=[dict(text=text)],proposal=proposal,premises=list(premises))
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(value)},'finish_reason':'stop'}]})
    return a.ResearchService(stores.paths,selection=Selection(provider='openrouter',model='fixture/model:free'),transport=httpx.MockTransport(handle)),calls


def run(stores,proposal,question='Give me the finished 60.',**kwargs):
    svc,calls=service(stores,proposal)
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    result=svc.run(a.ResearchRequest(scope='conversation',question=question,**kwargs))
    assert result['status']=='answered',result
    assert len(calls)==1 and before=={k:p.read_bytes() for k,p in stores.paths.items()}
    return result['answer']['proposal']


def active(stores,cards):
    with stores.snapshot() as (dbs,errors):
        catalog=Collection(SnapshotCards(stores.paths['cards'],dbs['cards']),stores.paths['collection']).catalog()[0]
        entries=[dict(identity=deck_identity(catalog[p]),name=catalog[p]['card']['name'],category=catalog[p]['card']['category'],quantity=n,allocations=[dict(printing_id=p,variant='normal',quantity=n)]) for p,n in cards]
    with sqlite3.connect(stores.paths['workspace']) as db:
        doc=json.loads(db.execute('SELECT document FROM workspace').fetchone()[0]);doc['entries']=entries
        db.execute('UPDATE workspace SET document=?',(json.dumps(doc),))
    return doc


def test_final_rogue_sixty_and_quality_are_separate(stores):
    result=run(stores,list_proposal(legal()))
    assert result['total_cards']==60 and result['validation_status']=='VALIDATED'
    assert result['legality_status']=='LEGAL_SUPPORTED_CHECKS'
    assert result['unresolved']==[] and all(r['card_id'] and r['printing_id'] for r in result['cards'])
    assert any('Darkness' in s for s in result['strategic_diagnostics'])
    assert result['writes_performed'] is False


def test_role_first_single_prize_basic_draw_candidates(stores):
    result=run(stores,list_proposal([dict(quantity=2,role='low-commitment single-prize draw engine')]),question='What specific cards would you add?')
    options=result['alternatives'][0]['candidates']
    assert options and any(r['printing_id']=='qa-draw' for r in options)
    assert all(r['printed']['stage']=='Basic' and not r['printed'].get('suffix') for r in options)
    assert result['resolution_status']=='UNRESOLVED'


def test_remembered_illegal_card_keeps_role_and_offers_legal_repair(stores):
    result=run(stores,list_proposal([row('qa-old',2,'Pokémon recovery'),row('qa-pikachu',4),row('qa-energy',54)]))
    assert result['validation_status']=='NEEDS_REPAIR'
    assert result['unresolved'][0]['state']=='illegal'
    assert any(r['printing_id']=='qa-recover' for r in result['alternatives'][0]['candidates'])
    assert all(r['standard'] for r in result['alternatives'][0]['candidates'])


def test_partial_slots_and_later_finalize_use_ephemeral_proposal(stores):
    draft=list_proposal([row('qa-pikachu',3),dict(quantity=2,role='secondary attacker')])
    svc,calls=service(stores,draft)
    first=svc.run(a.ResearchRequest(scope='conversation',question="I'm not ready for a 60 yet. Just sketch the shell."))
    report=first['answer']['proposal'];assert report['lifecycle']=='DRAFT' and report['unresolved']
    # The next mocked model resolves the slots; no automatic second call occurred.
    key=first['conversation_id'];svc2,calls2=service(stores,list_proposal(legal()));svc2.conversations=svc.conversations
    second=svc2.run(a.ResearchRequest(scope='conversation',question='Okay, resolve the remaining slots and give me the 60.',conversation_id=key))
    prompt=json.loads(calls2[0]['messages'][1]['content'])
    assert prompt['previous_proposal']==d.Proposal.model_validate(draft).model_dump(mode='json')
    assert second['answer']['proposal']['validation_status']=='VALIDATED'
    assert len(calls)==len(calls2)==1


def test_two_ace_specs_return_explanation_and_role_repair(stores):
    result=run(stores,list_proposal([row('qa-pikachu',4),row('qa-ace1',1,'draw'),row('qa-ace2',1,'Pokémon recovery'),row('qa-energy',54)]))
    assert result['legality_status']=='INVALID'
    assert any('ACE SPEC' in s for s in result['hard_validation'])
    assert any('Keep one ACE Draw' in s for s in result['repair_notes'])
    assert result['alternatives'] and any(r['printing_id']=='qa-recover' for r in result['alternatives'][-1]['candidates'])


def test_copy_limits_and_evolution_warnings(stores):
    result=run(stores,list_proposal([row('qa-pikachu',5),row('qa-evolution',1),row('qa-energy',54)]))
    assert any('normal limit is 4' in s for s in result['hard_validation'])
    assert any('Missing Basic' in s for s in result['strategic_diagnostics'])


def test_active_diff_exact_source_counts_and_no_writes(stores):
    doc=active(stores,[('qa-pikachu',4),('qa-energy',56)])
    proposal=dict(kind='diff',adds=[row('qa-draw',2)],removes=[row('qa-energy',2)],rationale='A small draw engine test.')
    result=run(stores,proposal,question='Give me the exact cards and quantities you would change.',include_deck=True,revision=7)
    assert result['deck_id']==doc['id'] and result['source_revision']==7
    assert result['removes'][0]['current_quantity']==56 and result['removes'][0]['validated']
    assert result['adds'][0]['current_quantity']==0 and result['total_cards']==60
    assert result['validation_status']=='VALIDATED'


def test_missing_cut_is_explained_with_real_source_choices(stores):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    result=run(stores,dict(kind='diff',removes=[row('qa-draw',2)],adds=[row('qa-recover',2)]),include_deck=True,revision=7)
    assert result['removes'][0]['current_quantity']==0 and not result['removes'][0]['validated']
    assert result['validation_status']=='NEEDS_REPAIR'
    assert any('source_candidates' in item for item in result['alternatives'])


def test_stale_revision_during_inference_returns_visible_qualification(stores):
    def update():
        with sqlite3.connect(stores.paths['workspace']) as db:db.execute('UPDATE workspace SET revision=revision+1')
    svc,calls=service(stores,dict(kind='diff',adds=[row('qa-draw',1)]),hook=update)
    result=svc.run(a.ResearchRequest(scope='conversation',question='What specific cards would you add?',include_deck=True,revision=7))
    assert result['status']=='answered' and result['answer']['proposal']['validation_status']=='STALE'
    assert len(calls)==1


def test_wrong_named_matchup_premise_corrects_without_blank_response(stores):
    premise=dict(name='Alakazam',printing_id='qa-alakazam1',expected_text='Heal 20 damage.')
    svc,calls=service(stores,premises=[premise],text='Alakazam heals damage, so plan around repeated healing.')
    result=svc.run(a.ResearchRequest(scope='conversation',question='How competitive is this against Alakazam?'))
    assert result['status']=='answered' and len(calls)==1
    assert result['answer']['proposal']['premises'][0]['status']=='corrected'
    assert 'plan around repeated healing' not in a.canonical(result['answer'])
    assert 'Draw 2 cards.' in a.canonical(result['answer']['proposal'])


def test_ambiguous_variant_is_not_arbitrarily_selected(stores):
    result=run(stores,list_proposal([dict(name='Alakazam',quantity=2)]))
    assert result['unresolved'][0]['state']=='ambiguous'
    assert len(result['alternatives'][0]['candidates'])>=2


def test_invalid_proposal_shape_does_not_remove_conversation(stores):
    svc,calls=service(stores,dict(kind='list',cards=[dict(name='Pikachu ex',quantity='two')]))
    result=svc.run(a.ResearchRequest(scope='conversation',question='Give me the finished 60.'))
    assert result['status']=='answered' and len(calls)==1
    assert 'not established a validated' in result['answer']['paragraphs'][-1]['text']


def test_add_another_and_excessive_cuts_use_actual_counts(stores):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    result=run(stores,dict(kind='diff',adds=[row('qa-pikachu',1)],removes=[row('qa-energy',1)]),include_deck=True,revision=7)
    assert result['adds'][0]['current_quantity']==4
    assert any('5 copies' in s for s in result['hard_validation'])
    result=run(stores,dict(kind='diff',removes=[row('qa-pikachu',3),row('qa-pikachu',2)]),include_deck=True,revision=7)
    assert result['removes'][0]['validated'] and not result['removes'][1]['validated']


def test_basic_energy_functional_identity_and_printing_separation(stores):
    result=run(stores,list_proposal([row('qa-pikachu',4),row('qa-energy',56)]))
    energy=next(r for r in result['cards'] if r['category']=='Energy')
    assert energy['card_id']=='deck-basic-energy:Lightning' and energy['printing_id']=='qa-energy'
    assert result['validation_status']=='VALIDATED'


def test_malformed_name_id_pair_cannot_borrow_printing_identity(stores):
    result=run(stores,list_proposal([dict(name='Fictional Card',printing_id='qa-pikachu',quantity=4),row('qa-energy',56)]))
    assert result['unresolved'][0]['state']=='name_printing_mismatch'
    assert not any(r['canonical_name']=='Pikachu ex' for r in result['cards'])


def test_concept_preserving_repair_keeps_original_core(stores):
    result=run(stores,list_proposal([row('qa-pikachu',4),row('qa-old',2,'Pokémon recovery'),row('qa-energy',54)]))
    assert next(r for r in result['cards'] if r['printing_id']=='qa-pikachu')['quantity']==4
    assert result['name']=='Weird Pikachu' and result['alternatives'][0]['role']=='Pokémon recovery'


def test_never_open_write_connection_during_resolution(stores,monkeypatch):
    connect=sqlite3.connect
    def guarded(path,*args,**kwargs):
        assert kwargs.get('uri') and 'mode=ro' in str(path)
        return connect(path,*args,**kwargs)
    monkeypatch.setattr(sqlite3,'connect',guarded)
    run(stores,list_proposal(legal()))


def test_cutting_an_illegal_card_can_produce_a_legal_proposal(stores):
    active(stores,[('qa-pikachu',4),('qa-old',2),('qa-energy',54)])
    result=run(stores,dict(kind='diff',removes=[row('qa-old',2)],adds=[row('qa-recover',2)]),include_deck=True,revision=7)
    assert result['validation_status']=='VALIDATED' and result['unresolved']==[]


def test_resolution_secret_is_quarantined_before_response_attachment(stores,monkeypatch):
    secret='post-resolution-fixture-secret-abcdef'
    monkeypatch.setenv('POKELAB_GEMINI_API_KEY',secret)
    monkeypatch.setattr(d,'evaluate',lambda *args:({'repair_notes':[secret]},[],set()))
    svc,_=service(stores,list_proposal(legal()))
    result=svc.run(a.ResearchRequest(scope='conversation',question='Give me the 60.'))
    assert result['status']=='invalid_answer_contract'
    assert secret not in a.canonical(result) and not svc.conversations.items


@pytest.mark.parametrize('question,stage',[
 ('What if we tried Munkidori?','EXPLORE'),('Could we make it better?','EXPLORE'),
 ('Sketch me the shell.','DRAFT'),('Tell me what to cut and add.','RECOMMEND'),
 ('Give me the PTCGL list.','FINALIZE'),('I hate that draw engine, but do not change the Pikachu concept.','EXPLORE'),
])
def test_lifecycle_does_not_force_exploration_into_validation(question,stage):assert d.lifecycle(question)==stage
