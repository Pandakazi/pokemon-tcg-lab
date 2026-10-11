"""Mock-only FINALIZE completion, Standard resolution and pending repair regressions."""
import json
import sqlite3
from copy import deepcopy
import httpx
import pytest
from tcg_lab.card_db import SQLiteCards
from pokelab import agent_research as a
from pokelab.agent_providers import Selection
from test_agent_deck_proposals import stores,active
from test_card_pool_research import sources,setup,research,offline


def deck(rows):
    return '<POKELAB_ACTIONS>'+json.dumps({'type':'generated_deck','name':'Keep the core','cards':[{'card_name':name,'printing_id':printing,'quantity':n,'role':role} for name,printing,n,role in rows]})+'</POKELAB_ACTIONS>'

FULL=[('Pikachu ex','qa-pikachu',4,'main attacker'),('Recovery Tool','qa-recover',4,'recovery'),('Lightning Energy','qa-energy',52,'energy')]
BAD=[('Pikachu ex','qa-pikachu',4,'main attacker'),('Old Recovery','qa-old',4,'recovery'),('Lightning Energy','qa-energy',52,'energy')]


def service(stores,replies):
    calls=[]
    def handle(req):
        body=json.loads(req.content);calls.append(body)
        assert 'response_format' not in body
        env=json.loads(body['messages'][1]['content'])
        assert env['build_constraints']['format']=='standard'
        reply=replies[min(len(calls)-1,len(replies)-1)]
        return reply if isinstance(reply,httpx.Response) else httpx.Response(200,json={'choices':[{'message':{'content':reply},'finish_reason':'stop'}]})
    return a.ResearchService(stores.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle)),calls


def test_finalize_repairs_illegal_role_once_then_completes(stores):
    svc,calls=service(stores,[deck(BAD),deck(FULL)])
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    result=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete legal 60-card Standard deck.'))
    assert result['status']=='answered',result
    report=result['answer']['proposal']
    assert report['validation_status']=='VALIDATED' and report['total_cards']==60 and report['unresolved']==[]
    assert all(r['standard'] is True and r['printed']['legal']['standard'] is True for r in report['cards'])
    requirements=json.loads(calls[1]['messages'][1]['content'])['repair']
    assert requirements['total']==56 and requirements['unresolved'][0]['role']=='recovery'
    assert requirements['alternatives'][0]['candidates']
    assert len(calls)==2 and before=={k:p.read_bytes() for k,p in stores.paths.items()}
    again=svc.run(a.ResearchRequest(scope='conversation',question='Recount that deck.',conversation_id=result['conversation_id']))
    assert again['answer']['proposal']['total_cards']==60 and len(calls)==2


def test_failed_repair_is_bounded_and_stored_as_pending(stores):
    svc,calls=service(stores,[deck(BAD)])
    result=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete legal 60-card deck.'))
    assert len(calls)==2 and result['answer']['completion']['status']=='incomplete'
    assert result['answer']['proposal']['total_cards']==56
    assert svc.conversations.get(result['conversation_id'])['artifacts']['generated_deck']['pending']


@pytest.mark.parametrize('question',['Finish it.','fix it','Ok so do that.','complete the list','fill the rest','resolve those','make it legal','finish the 60'])
def test_pending_confirmations_execute_repair(stores,question):
    svc,calls=service(stores,[deck(BAD),deck(BAD),deck(FULL)])
    first=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete legal 60-card deck.'))
    result=svc.run(a.ResearchRequest(scope='conversation',question=question,conversation_id=first['conversation_id']))
    assert result['answer']['proposal']['validation_status']=='VALIDATED',result
    context=json.loads(calls[2]['messages'][1]['content'])
    assert context['repair']['name']=='Keep the core' and context['lifecycle']=='FINALIZE'
    assert len(calls)==3


def test_repair_explanation_and_transport_failure_preserve_original(stores):
    for bad in ['I would add recovery.',httpx.Response(429,json={'error':{'code':429}})]:
        svc,calls=service(stores,[deck(BAD),bad])
        result=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete legal 60-card deck.'))
        assert result['answer']['proposal']['total_cards']==56 and len(calls)==2
        assert result['answer']['completion']['status']=='incomplete'


def test_legal_equivalent_printing_is_normalized(stores):
    with stores.snapshot() as (dbs,_):raw=json.loads(dbs['cards'].execute("SELECT raw FROM cards WHERE id='qa-recover'").fetchone()[0])
    old=deepcopy(raw);old.update(id='qa-historical',legal={'standard':False})
    SQLiteCards(stores.paths['cards']).put(old)
    with sqlite3.connect(stores.paths['cards']) as db:db.execute("UPDATE cards SET game='tcg' WHERE id='qa-historical'")
    rows=[FULL[0],('Recovery Tool','qa-historical',4,'recovery'),FULL[2]]
    svc,calls=service(stores,[deck(rows)])
    result=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete 60-card Standard deck.'))
    assert result['answer']['proposal']['validation_status']=='VALIDATED'
    assert result['answer']['proposal']['cards'][1]['printing_id']=='qa-recover'
    assert len(calls)==1


def test_unresolved_identity_cannot_independently_gain_printed_facts(stores):
    ambiguous=[FULL[0],('Alakazam',None,4,'draw support'),FULL[2]]
    svc,calls=service(stores,[deck(ambiguous),deck(ambiguous),'Alakazam has an Ability called First that draws cards. I would preserve the core.'])
    first=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete legal 60-card deck.'))
    result=svc.run(a.ResearchRequest(scope='conversation',question='Why that support?',conversation_id=first['conversation_id']))
    assert 'First' not in json.dumps(result['answer'])
    assert not any(e.get('title')=='Alakazam' for e in result['answer']['facts'])
    assert result['answer']['fact_reviews'][0]['status']=='unresolved'


def test_explanation_does_not_trigger_confirmation_repair(stores):
    svc,calls=service(stores,[deck(BAD),deck(BAD),'I could not resolve the recovery slot within the bounded pass.'])
    first=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete legal 60-card deck.'))
    result=svc.run(a.ResearchRequest(scope='conversation',question="Why didn't you finish it?",conversation_id=first['conversation_id']))
    assert 'repair' not in json.loads(calls[-1]['messages'][1]['content']) and len(calls)==3
    assert result['status']=='answered'

@pytest.mark.parametrize('question',['Why?','What are you basing that on?','Is that proven?','Show me the tournament data.','Where does the card say that?','Give me your sources.'])
def test_proof_questions_surface_existing_evidence(stores,question):
    from pokelab.agent_conversation import context
    envelope=context(a.ResearchRequest(scope='conversation',question=question),stores,dict(turns=[],printings=[]))
    assert envelope['proof_requested'] is True


def test_confirmation_requires_pending_artifact_and_new_request_is_not_hijacked():
    from pokelab.agent_artifacts import pending_repair
    assert pending_repair('Ok so do that.',{}) is None
    history={'artifacts':{'generated_deck':{'pending':True}}}
    assert pending_repair('Create a different deck instead.',history) is None
    assert pending_repair('Do not finish that.',history) is None


def test_resolved_generated_identity_controls_facts_over_active_deck(stores):
    # This deliberately sparse identity/fact fixture retains 52 Energy. Give
    # its synthetic core a printed scaling reason, independent of shape tests.
    with sqlite3.connect(stores.paths['cards']) as db:
        raw=json.loads(db.execute("SELECT raw FROM cards WHERE id='qa-pikachu'").fetchone()[0])
    raw['attacks'][0]['effect']='This attack does 20 damage for each Energy attached to this Pokémon.'
    SQLiteCards(stores.paths['cards']).put(raw)
    with sqlite3.connect(stores.paths['cards']) as db:db.execute("UPDATE cards SET game='tcg' WHERE id='qa-pikachu'")
    active(stores,[('qa-alakazam2',1),('qa-energy',59)])
    rows=[FULL[0],('Alakazam','qa-alakazam1',4,'draw support'),FULL[2]]
    svc,calls=service(stores,[deck(rows),'Alakazam has an Ability called First.'])
    first=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete 60-card deck with Alakazam, Pikachu ex and Lightning Energy.',include_deck=True,revision=7))
    assert first['answer']['proposal']['validation_status']=='VALIDATED'
    result=svc.run(a.ResearchRequest(scope='conversation',question='Explain that support.',include_deck=True,revision=7,conversation_id=first['conversation_id']))
    facts=result['answer']['facts']
    assert any(f.get('printing')=='qa-alakazam1' for f in facts)
    assert not any(f.get('printing')=='qa-alakazam2' for f in facts)
