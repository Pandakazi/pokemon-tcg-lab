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
    from pokelab.agent_deck_sandbox import small_repair
    repair_expected=small_repair(result['answer']['proposal']) and d.lifecycle(question)=='FINALIZE' and result['answer']['proposal']['kind']=='list' and result['answer']['proposal']['validation_status']!='VALIDATED'
    assert len(calls)==(2 if repair_expected else 1) and before=={k:p.read_bytes() for k,p in stores.paths.items()}
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
    result=run(stores,list_proposal([dict(name='Alakazam',quantity=2)]),question='Give me the finished 60 with Alakazam.')
    assert result['unresolved'][0]['state']=='ambiguous'
    assert len(result['alternatives'][0]['candidates'])>=2


def test_invalid_proposal_shape_does_not_remove_conversation(stores):
    svc,calls=service(stores,dict(kind='list',cards=[dict(name='Pikachu ex',quantity='two')]))
    result=svc.run(a.ResearchRequest(scope='conversation',question='Give me the finished 60.'))
    assert result['status']=='answered' and len(calls)==1
    assert 'missing_artifact' in result['answer']['notices']


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


@pytest.mark.parametrize('question,include_deck',[
    ('How does this deck work?',True),
    ('Can we make it better?',True),
    ('Is there a way to make it better or is it pretty maxed out?',True),
    ('Explain a weird deck concept.',False),
])
def test_gemini_ordinary_wire_contract_twice(stores,monkeypatch,question,include_deck):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    calls=[]
    def no_resolution(*args,**kwargs):
        raise AssertionError('Ordinary explanation must not require proposal evaluation')
    monkeypatch.setattr(d,'evaluate',no_resolution)
    def handle(req):
        body=json.loads(req.content);calls.append(body)
        assert 'response_format' not in body
        assert 'not a JSON answer envelope' in body['messages'][0]['content']
        value=dict(version='pokelab-conversation-answer-v1',paragraphs=[dict(text='The core has a coherent plan; consider consistency before changes.')])
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(value)},'finish_reason':'stop'}]})
    svc=a.ResearchService(stores.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle))
    conversation=None
    for _ in range(2):
        result=svc.run(a.ResearchRequest(scope='conversation',question=question,include_deck=include_deck,revision=7 if include_deck else None,conversation_id=conversation))
        assert result['status']=='answered' and 'proposal' not in result['answer']
        conversation=result['conversation_id']
    assert len(calls)==2


def test_concrete_wire_contract_stays_available():
    for question in ('Give me exact cards and quantities to add/remove.','Give me the final 60.'):
        system,schema=c.provider_contract(d.lifecycle(question))
        assert schema is None and 'Respond in natural prose' in system


@pytest.mark.parametrize('question',[
 'Give me the exact card names and quantities you would change, what you would remove, and why.',
 'Okay. Make those changes concrete. What exactly comes out and what exactly goes in?',
 'What are the 3 weakest cards and what three cards would you replace them with and why?',
 'What would you replace these three slots with?',
 'Add another Area Zero and another Grass Energy.',
 'What would you replace those three with?',
])
def test_pm_counts_are_authoritative_in_final_answer(stores,question):
    db=SQLiteCards(stores.paths['cards'])
    for ident,name,category in [('area','Area Zero Underdepths','Trainer'),('grass','Grass Energy','Energy'),('night','Night Stretcher','Trainer'),('cyrano','Cyrano','Trainer'),('tower','Jamming Tower','Trainer'),('red','Special Red Card','Trainer')]:
        db.put(dict(id=ident,name=name,category=category,energyType='Normal' if category=='Energy' else None,types=['Grass'] if category=='Energy' else [],legal={'standard':True},variants={'normal':True},set={'id':'qa'},localId=ident,rarity='Common'))
    with sqlite3.connect(stores.paths['cards']) as conn:conn.execute("UPDATE cards SET game='tcg'")
    active(stores,[('area',3),('grass',6),('night',2),('cyrano',2),('tower',1),('red',1),('qa-pikachu',4),('qa-energy',41)])
    with sqlite3.connect(stores.paths['workspace']) as conn:conn.execute('UPDATE workspace SET revision=158')
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    proposal=dict(kind='diff',adds=[row('area',1),row('grass',1),dict(name='',quantity=1,role='consistency tool')],removes=[row('tower',1),row('cyrano',1)])
    calls=[]
    def handle(req):
        body=json.loads(req.content);calls.append(body)
        assert 'response_format' not in body
        envelope=json.loads(body['messages'][1]['content'])
        assert envelope['lifecycle']=='RECOMMEND'
        value=dict(version='pokelab-conversation-answer-v1',paragraphs=[dict(text='Add the 3rd Area Zero Underdepths and an 8th Grass Energy or an extra consistency tool.')],proposal=proposal)
        actions={'changes':[{'action':'remove','card_name':'Jamming Tower','quantity':1},{'action':'remove','card_name':'Cyrano','quantity':1},{'action':'add','card_name':'Area Zero Underdepths','quantity':1},{'action':'add','card_name':'Grass Energy','quantity':1},{'action':'add','role':'consistency tool','quantity':1}]}
        text=value['paragraphs'][0]['text']+' This is a consistency hypothesis. <POKELAB_ACTIONS>'+json.dumps(actions)+'</POKELAB_ACTIONS>'
        return httpx.Response(200,json={'choices':[{'message':{'content':text},'finish_reason':'stop'}]})
    svc=a.ResearchService(stores.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle))
    result=svc.run(a.ResearchRequest(scope='conversation',question=question,include_deck=True,revision=158))
    assert result['status']=='answered'
    prose=' '.join(p['text'] for p in result['answer']['paragraphs'])
    assert '3rd' not in prose and '8th' not in prose and 'or an extra' not in prose
    report=result['answer']['proposal']
    assert [(r['current_quantity'],r['resulting_quantity']) for r in report['adds']]==[(3,4),(6,7)]
    assert report['unresolved']
    assert len(calls)==1 and before=={k:p.read_bytes() for k,p in stores.paths.items()}


def test_missing_concrete_diff_cannot_display_unchecked_prose(stores):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    svc,calls=service(stores,text='Add the 8th Grass Energy or a consistency tool.')
    result=svc.run(a.ResearchRequest(scope='conversation',question='What exactly comes out and what exactly goes in?',include_deck=True,revision=7))
    assert result['status']=='answered'
    prose=' '.join(p['text'] for p in result['answer']['paragraphs'])
    assert '8th' not in prose and 'missing_artifact' in result['answer']['notices'] and len(calls)==1


@pytest.mark.parametrize('rationale,shown',[
 ('I would test a draw engine to reduce setup pressure while preserving the core.',True),
 ('This improves the Dragapult matchup by 8%.',False),
 ('Add the 8th Grass Energy.',False),
])
def test_strategy_without_empirical_permission_gate(stores,rationale,shown):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    proposal=dict(kind='diff',adds=[row('qa-draw',2)],removes=[row('qa-energy',2)],rationale=rationale)
    svc,calls=service(stores,proposal)
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    first=svc.run(a.ResearchRequest(scope='conversation',question='Is there a way to make it better?',include_deck=True,revision=7))
    result=svc.run(a.ResearchRequest(scope='conversation',question='Give me exact cards and quantities.',include_deck=True,revision=7,conversation_id=first['conversation_id']))
    assert first['status']==result['status']=='answered'
    envelope=json.loads(calls[-1]['messages'][1]['content'])
    assert 'empirical-tournament-evidence-not-supplied' in envelope['omissions']
    assert 'without demanding tournament proof' in calls[-1]['messages'][0]['content']
    report=result['answer']['proposal']
    assert report['validation_status']=='VALIDATED' and report['source_revision']==7
    prose=' '.join(p['text'] for p in result['answer']['paragraphs'])
    assert (rationale in prose)==shown
    if shown:assert 'Strategic hypothesis (not a proven tournament improvement)' not in prose
    if '8%' in rationale:assert result['empirical_qualification'] is True
    assert report['removes'][0]['current_quantity']==56 and report['removes'][0]['resulting_quantity']==54
    assert len(calls)==2 and before=={k:p.read_bytes() for k,p in stores.paths.items()}


def test_role_only_proposal_retains_strategy_without_proof(stores):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    rationale='I would test a consistency slot before changing the main attacker.'
    svc,calls=service(stores,dict(kind='diff',removes=[row('qa-energy',1)],adds=[dict(name='',quantity=1,role='consistency')],rationale=rationale))
    result=svc.run(a.ResearchRequest(scope='conversation',question='Give me exact cards and quantities.',include_deck=True,revision=7))
    assert result['status']=='answered'
    prose=' '.join(p['text'] for p in result['answer']['paragraphs'])
    assert rationale in prose and result['answer']['proposal']['unresolved'] and len(calls)==1


@pytest.mark.parametrize('block,expected',[
 ('<POKELAB_ACTIONS>{"changes":[{"action":"remove","card_name":"Lightning Energy","quantity":1},{"action":"add","card_name":"Draw Helper","quantity":1}]}</POKELAB_ACTIONS>','valid'),
 ('','missing'),
 ('<POKELAB_ACTIONS>{broken}</POKELAB_ACTIONS>','malformed'),
 ('<POKELAB_ACTIONS>{"changes":[{"action":"add","card_name":"Draw Helper","quantity":1},{"action":"remove","quantity":"bad"}]}</POKELAB_ACTIONS>','partial'),
 ('<POKELAB_ACTIONS>{"changes":[{"action":"add","role":"single-prize draw support","quantity":1}]}</POKELAB_ACTIONS>','role'),
])
def test_hybrid_natural_prose_survives_optional_actions(stores,block,expected):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    calls=[]
    def handle(req):
        body=json.loads(req.content);calls.append(body)
        assert 'response_format' not in body
        assert 'Return JSON only' not in body['messages'][0]['content']
        prose='I would test a draw engine. This looks like a consistency hypothesis. '
        return httpx.Response(200,json={'choices':[{'message':{'content':prose+block},'finish_reason':'stop'}]})
    svc=a.ResearchService(stores.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle))
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    result=svc.run(a.ResearchRequest(scope='conversation',question='Give me exact cards and quantities.',include_deck=True,revision=7))
    assert result['status']=='answered'
    prose=' '.join(p['text'] for p in result['answer']['paragraphs'])
    assert 'consistency hypothesis' in prose and 'POKELAB_ACTIONS' not in a.canonical(result)
    if expected in ('missing','malformed'):
        assert 'proposal' not in result['answer'] and 'missing_artifact' in result['answer']['notices']
    elif expected=='valid':assert result['answer']['proposal']['validation_status']=='VALIDATED'
    else:assert result['answer']['proposal']['validation_status']=='NEEDS_REPAIR'
    assert len(calls)==1 and before=={k:p.read_bytes() for k,p in stores.paths.items()}


def test_hybrid_withholds_state_unit_without_rewriting_remaining_strategy(stores):
    svc,_=service(stores,text='Add the 3rd Area Zero because the stadium supports the core. This improves setup flexibility. This raises win rate by 8%.')
    result=svc.run(a.ResearchRequest(scope='conversation',question='Give me exact changes.'))
    assert result['answer']['paragraphs']==[dict(text='This improves setup flexibility.',evidence=[])]
    assert result['empirical_qualification']


@pytest.mark.parametrize('question',[
 'What three cards would you replace them with?',
 'What would you replace these slots with?',
 'What exact changes would you make?',
 'Replace the weakest two cards.',
 'What comes out and what goes in?',
 'Give me the exact cards and quantities.',
])
def test_explicit_substitution_routes_concrete(question):
    assert d.lifecycle(question)=='RECOMMEND'
    assert c.provider_contract(d.lifecycle(question),True)[1] is None


def test_weakness_analysis_is_not_a_substitution_request():
    assert d.lifecycle('What are the weakest parts of this deck?')=='EXPLORE'


@pytest.mark.parametrize('payload',[
 '<POKELAB_ACTIONS>{"changes":[{"action":"remove","card_name":"Draw Helper","quantity":1},{"action":"add","card_name":"Recovery Tool","quantity":1}]}</POKELAB_ACTIONS>',
 '<POKELAB_ACTIONS>{bad}</POKELAB_ACTIONS>',
 '',
])
def test_absent_explicit_cut_cannot_survive_as_strategy(stores,payload):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    calls=[]
    def handle(req):
        body=json.loads(req.content);calls.append(body)
        assert 'response_format' not in body
        text='Draw Helper is a liability in this deck. This makes the proposed cut worthwhile. Improving consistency is a reasonable goal. '+payload
        return httpx.Response(200,json={'choices':[{'message':{'content':text},'finish_reason':'stop'}]})
    svc=a.ResearchService(stores.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle))
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    result=svc.run(a.ResearchRequest(scope='conversation',question='Cut Draw Helper and add another Recovery Tool.',include_deck=True,revision=7))
    assert result['status']=='answered'
    prose=' '.join(p['text'] for p in result['answer']['paragraphs'])
    assert 'is a liability' not in prose and 'worthwhile' not in prose
    assert result['answer']['proposal']['removes'][0]['current_quantity']==0 and 'consistency is a reasonable goal' in prose
    assert result['answer']['proposal']['removes'][0]['validated'] is False
    assert len(calls)==1 and before=={k:p.read_bytes() for k,p in stores.paths.items()}


def test_integrity_intents_and_empirical_audit_route():
    for q in ['Cut Squawkabilly ex and add another Boss\'s Orders.','Add another Area Zero.','Add another Grass Energy.','What would you replace those three with?']:
        assert d.lifecycle(q)=='RECOMMEND'
    q='Which of these recommendations are proven by tournament results and which are just your structural judgment?'
    assert d.lifecycle(q)=='EXPLORE'
    assert c.provider_contract(d.lifecycle(q))[1] is None


def test_stale_another_and_ordinals_do_not_survive(stores):
    for state in ['A second Area Zero Underdepths helps.','A third Area Zero Underdepths helps.','A fourth or fifth Grass Energy helps.','Another Area Zero is already present.']:
        svc,_=service(stores,text=state+' Consistency is a hypothesis.')
        result=svc.run(a.ResearchRequest(scope='conversation',question='Give me exact changes.'))
        assert result['answer']['paragraphs']==[dict(text='Consistency is a hypothesis.',evidence=[])]


def test_full_deck_addition_requests_balancing_cuts_and_preserves_core(stores):
    active(stores,[('qa-pikachu',4),('qa-draw',2),('qa-recover',4),('qa-energy',50)])
    calls=[]
    def handle(req):
        body=json.loads(req.content);calls.append(body)
        assert 'propose balancing' in body['messages'][0]['content']
        assert 'Preserve core' in body['messages'][0]['content']
        actions={'changes':[{'action':'add','card_name':'Draw Helper','quantity':2},{'action':'remove','card_name':'Recovery Tool','quantity':2}],'rationale':'I would test trimming redundant recovery to preserve the main attacker and draw engine.'}
        text='I would preserve the core and test a support change. <POKELAB_ACTIONS>'+json.dumps(actions)+'</POKELAB_ACTIONS>'
        return httpx.Response(200,json={'choices':[{'message':{'content':text},'finish_reason':'stop'}]})
    svc=a.ResearchService(stores.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle))
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    result=svc.run(a.ResearchRequest(scope='conversation',question='Add two Draw Helper.',include_deck=True,revision=7))
    report=result['answer']['proposal']
    assert report['total_cards']==60 and report['validation_status']=='VALIDATED'
    assert sum(r['quantity'] for r in report['removes'])==2
    assert all(r['canonical_name']!='Pikachu ex' for r in report['removes'])
    assert any('redundant recovery' in p['text'] for p in result['answer']['paragraphs'])
    assert before=={k:p.read_bytes() for k,p in stores.paths.items()} and len(calls)==1


def test_evidence_boundary_names_recent_swaps(stores):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    proposal=dict(kind='diff',adds=[row('qa-draw',1)],removes=[row('qa-energy',1)])
    svc,calls=service(stores,proposal,text='Draw Helper and Lightning Energy are changes I would test, not proven upgrades.')
    first=svc.run(a.ResearchRequest(scope='conversation',question='Give me exact cards and quantities.',include_deck=True,revision=7))
    result=svc.run(a.ResearchRequest(scope='conversation',question='Which of these recommendations are proven by tournament results and which are just your structural judgment?',include_deck=True,revision=7,conversation_id=first['conversation_id']))
    prose=' '.join(p['text'] for p in result['answer']['paragraphs'])
    assert 'Draw Helper and Lightning Energy' in prose and 'not proven upgrades' in prose
    context=json.loads(calls[-1]['messages'][1]['content'])
    assert context['artifacts']['proposed_deck_changes']['report']['adds'][0]['canonical_name']=='Draw Helper'


def test_concrete_referents_are_explicit(stores):
    active(stores,[('qa-pikachu',4),('qa-draw',1),('qa-recover',1),('qa-dark',1),('qa-energy',53)])
    svc,calls=service(stores,text='The three situational slots to review are Draw Helper, Recovery Tool, and Darkness Energy.')
    first=svc.run(a.ResearchRequest(scope='conversation',question='Which three slots would you review?',include_deck=True,revision=7))
    def followup(req):
        body=json.loads(req.content);calls.append(body)
        assert 'Draw Helper, Recovery Tool, and Darkness Energy' in json.dumps(body)
        assert 'explicitly name the cards' in body['messages'][0]['content']
        actions={'changes':[{'action':'remove','card_name':name,'quantity':1} for name in ['Draw Helper','Recovery Tool','Darkness Energy']]+[{'action':'add','card_name':'Lightning Energy','quantity':3}]}
        text='By those three I mean Draw Helper, Recovery Tool, and Darkness Energy. I would test simplifying the support package. <POKELAB_ACTIONS>'+json.dumps(actions)+'</POKELAB_ACTIONS>'
        return httpx.Response(200,json={'choices':[{'message':{'content':text},'finish_reason':'stop'}]})
    svc.transport=httpx.MockTransport(followup)
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    result=svc.run(a.ResearchRequest(scope='conversation',question='What would you replace those three with?',include_deck=True,revision=7,conversation_id=first['conversation_id']))
    assert result['status']=='answered',result
    assert 'Draw Helper, Recovery Tool, and Darkness Energy' in result['answer']['paragraphs'][0]['text']
    assert result['answer']['proposal']['total_cards']==60
    assert before=={k:p.read_bytes() for k,p in stores.paths.items()}


def test_ambiguous_reference_can_ask_without_actions(stores):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    svc,_=service(stores,text='Do you mean the support cards or the Energy slots?')
    result=svc.run(a.ResearchRequest(scope='conversation',question='What would you replace those three with?',include_deck=True,revision=7))
    assert result['status']=='answered' and 'proposal' not in result['answer']
    assert sum(p['text'].count('?') for p in result['answer']['paragraphs'])==1
