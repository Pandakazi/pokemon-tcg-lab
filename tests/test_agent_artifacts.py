"""Architecture acceptance: structured artifacts, never prose arithmetic or live AI."""
import json
import httpx
import pytest
from pokelab import agent_conversation as c,agent_research as a
from pokelab.agent_providers import Selection
from test_agent_deck_proposals import stores,active
from test_card_pool_research import sources,setup,research,offline


def service(stores,answer):
    calls=[]
    def handle(req):
        body=json.loads(req.content);calls.append(body)
        assert 'response_format' not in body
        return httpx.Response(200,json={'choices':[{'message':{'content':answer},'finish_reason':'stop'}]})
    return a.ResearchService(stores.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle)),calls


def generated(count=52):
    return 'Trainer (32)\nTotal: 60\nThis is a complete legal deck.\n<POKELAB_ACTIONS>'+json.dumps({'type':'generated_deck','name':'Test concept','cards':[{'card_name':'Pikachu ex','printing_id':'qa-pikachu','quantity':4},{'card_name':'Recovery Tool','printing_id':'qa-recover','quantity':4},{'card_name':'Lightning Energy','printing_id':'qa-energy','quantity':count}]})+'</POKELAB_ACTIONS>'


@pytest.mark.parametrize('energy,total,status',[(51,59,'NEEDS_REPAIR'),(52,60,'VALIDATED')])
def test_finalize_structured_totals_and_local_recount(stores,monkeypatch,energy,total,status):
    svc,calls=service(stores,generated(energy));before={k:p.read_bytes() for k,p in stores.paths.items()}
    question='Create me a complete legal 60-card Dragapult ex deck and put it in list form. Make every slot an exact card, include category subtotals, and make sure the total is exactly 60.'
    assert c.lifecycle(question)=='FINALIZE'
    result=svc.run(a.ResearchRequest(scope='conversation',question=question))
    assert result['status']=='answered',result
    answer=result['answer'];report=answer['proposal']
    assert report['total_cards']==total and report['category_subtotals']=={'Pokemon':4,'Trainer':4,'Energy':energy}
    assert report['validation_status']==status
    assert answer['paragraphs']==[] and answer['artifact_id']
    import pokelab.agent_card_facts as facts
    monkeypatch.setattr(facts,'review',lambda *args,**kwargs:pytest.fail('Recount must not inspect printed claims'))
    for q in ['What exact cards and quantities are in the deck list you just proposed? Recount them and tell me the total.','show me that list again','what exact cards were in it?','how many cards was that?']:
        again=svc.run(a.ResearchRequest(scope='conversation',question=q,conversation_id=result['conversation_id']))
        assert again['execution']['provider_called'] is False
        assert again['answer']['proposal']['total_cards']==total
        assert [(r['printing_id'],r['quantity']) for r in again['answer']['proposal']['cards']]==[(r['printing_id'],r['quantity']) for r in report['cards']]
        assert again['answer']['artifact_id']==answer['artifact_id']
    assert len(calls)==(1 if total==60 else 2) and before=={k:p.read_bytes() for k,p in stores.paths.items()}


def test_generated_deck_separate_from_active_deck(stores):
    active(stores,[('qa-energy',60)])
    svc,_=service(stores,generated())
    result=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete 60-card deck.',include_deck=True,revision=7))
    assert result['answer']['proposal']['kind']=='list'
    assert result['answer']['proposal']['total_cards']==60
    assert svc.conversations.get(result['conversation_id'])['artifacts']['generated_deck']['report']['cards'][0]['canonical_name']=='Pikachu ex'


def test_missing_or_malformed_artifact_never_renders_false_final(stores):
    for block in ['', '<POKELAB_ACTIONS>{bad}</POKELAB_ACTIONS>']:
        svc,_=service(stores,'Trainer (32)\n31 Recovery Tool\nTotal: 60\nThis is a complete legal deck.\nI like a steady setup plan.\n'+block)
        result=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete legal 60-card deck.'))
        assert result['status']=='answered',result
        assert result['answer']['paragraphs']==[{'text':'I like a steady setup plan.','evidence':[]}]
        assert 'missing_artifact' in result['answer']['notices']
        assert not svc.conversations.get(result['conversation_id'])['artifacts']


def test_explicit_cut_does_not_silently_substitute(stores):
    active(stores,[('qa-energy',56),('qa-pikachu',4)])
    block={'type':'proposed_deck_changes','changes':[{'action':'remove','card_name':'Lightning Energy','quantity':1},{'action':'add','card_name':'Recovery Tool','quantity':1}]}
    svc,_=service(stores,'I would test recovery. <POKELAB_ACTIONS>'+json.dumps(block)+'</POKELAB_ACTIONS>')
    result=svc.run(a.ResearchRequest(scope='conversation',question='Cut Draw Helper and add another Recovery Tool.',include_deck=True,revision=7))
    report=result['answer']['proposal']
    assert [r['canonical_name'] for r in report['removes']]==['Draw Helper']
    assert report['removes'][0]['validated'] is False
    assert next(r for r in report['cards'] if r['canonical_name']=='Lightning Energy')['quantity']==56


def test_auto_cut_cannot_cancel_add(stores):
    active(stores,[('qa-energy',56),('qa-pikachu',4)])
    block={'changes':[{'action':'remove','card_name':'Lightning Energy','quantity':1},{'action':'add','card_name':'Lightning Energy','quantity':1}],'rationale':'I would test the setup tradeoff.'}
    svc,_=service(stores,'<POKELAB_ACTIONS>'+json.dumps(block)+'</POKELAB_ACTIONS>')
    result=svc.run(a.ResearchRequest(scope='conversation',question='Add another Lightning Energy.',include_deck=True,revision=7))
    report=result['answer']['proposal']
    assert report['removes'][0]['validated'] is False
    assert report['adds'][0]['resulting_quantity']==57
    assert report['validation_status']=='NEEDS_REPAIR'
    assert any('cannot cancel' in reason for reason in report['hard_validation'])
    assert 'setup tradeoff' in json.dumps(result['answer']['paragraphs'])


def test_pronoun_is_not_card_and_natural_conversation_has_no_schema(stores):
    svc,calls=service(stores,'That requires patience. I like this plan.')
    result=svc.run(a.ResearchRequest(scope='conversation',question='What do you think?'))
    assert result['status']=='answered'
    assert not result['answer']['fact_reviews'] and len(result['answer']['paragraphs'])==2
    assert 'Return JSON only' not in calls[0]['messages'][0]['content']


def test_printed_claim_uses_structured_review_not_injected_prose(stores):
    svc,_=service(stores,'Pikachu ex uses Wrong Storm to heal everything. I would preserve the core.')
    result=svc.run(a.ResearchRequest(scope='conversation',question='Explain this plan.'))
    assert result['answer']['paragraphs']==[{'text':'I would preserve the core.','evidence':[]}]
    assert result['answer']['fact_reviews'][0]['card']=='Pikachu ex'
    assert result['answer']['facts'][0]['value']['attacks'][0]['name']=='Spark'

def test_artifact_survives_prose_compaction_and_later_diff(stores):
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    svc,_=service(stores,generated())
    first=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete 60-card deck.'))
    session=first['conversation_id'];artifact_id=first['answer']['artifact_id']
    history=svc.conversations.get(session)
    history['turns']=[]  # exact artifact is independent of prose retention
    body={'type':'proposed_deck_changes','changes':[{'action':'remove','card_name':'Lightning Energy','quantity':1},{'action':'add','card_name':'Recovery Tool','quantity':1}]}
    svc.transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'choices':[{'message':{'content':'I would test recovery. <POKELAB_ACTIONS>'+json.dumps(body)+'</POKELAB_ACTIONS>'},'finish_reason':'stop'}]}))
    changed=svc.run(a.ResearchRequest(scope='conversation',question='Give me exact changes.',conversation_id=session,include_deck=True,revision=7))
    assert changed['answer']['proposal']['kind']=='diff'
    assert set(svc.conversations.get(session)['artifacts'])=={'generated_deck','proposed_deck_changes'}
    again=svc.run(a.ResearchRequest(scope='conversation',question='Recount that deck.',conversation_id=session))
    assert again['answer']['artifact_id']==artifact_id and again['answer']['proposal']['total_cards']==60
    assert again['execution']['provider_called'] is False


def test_selected_empirical_evidence_is_displayed_from_source(stores):
    from pokelab.agent_artifacts import present
    from pokelab.agent_hybrid import parse
    meta={};parse('<POKELAB_ACTIONS>{"changes":[],"fact_ids":["sample", "invented"]}</POKELAB_ACTIONS>',False,meta)
    source=dict(id='sample',kind='evidence',title='competitive',value={'window':'30','sample_size':15,'usage_percent':20})
    envelope={'evidence':[source],'lifecycle':'EXPLORE'}
    parsed=c.Answer(version='pokelab-conversation-answer-v1',paragraphs=[dict(text='I would test recovery.')],fact_ids=meta['fact_ids'])
    answer,qualified=present('I would test recovery.',parsed,None,set(),[],envelope,stores,a.ResearchRequest(scope='conversation',question='Which ideas have evidence?'))
    assert answer['facts']==[source] and not qualified and answer['notices']==[]

def test_oversized_artifact_cannot_be_presented_as_final():
    from pokelab.agent_artifacts import remember
    report=dict(kind='list',cards=[],adds=[],removes=[],alternatives=[],validation_status='VALIDATED',hard_validation=['x'*66000])
    artifacts=remember({},report,{'content_hash':'fixture'})
    assert not artifacts and report['validation_status']=='NEEDS_REPAIR'
    assert 'cannot be retained for recount' in report['hard_validation'][-1]
