"""Generated A -> discussion -> proposal -> local B, with no workspace writes."""
import json
from copy import deepcopy
import pytest
from pokelab import agent_research as a
from pokelab.agent_artifacts import clean_references
from test_agent_deck_completion import service,partial,addition,QUESTION,energy_engine
from test_agent_deck_proposals import stores,active
from test_card_pool_research import sources,setup,research,offline


def request(svc,key,question,**kwargs):
    return svc.run(a.ResearchRequest(scope='conversation',question=question,conversation_id=key,**kwargs))


def changes(env,n=1):
    return 'I would trade excess Energy for recovery flexibility. <POKELAB_ACTIONS>'+json.dumps(dict(type='proposed_deck_changes',changes=[
        dict(action='remove',**addition(env,'Lightning Energy',n)),dict(action='add',**addition(env,'Recovery Tool',n))],rationale='Test the recovery tradeoff.'))+'</POKELAB_ACTIONS>'


@pytest.mark.parametrize('question',['Critique your own deck.','Why did you choose these cards?','What are the weaknesses?','Is this too much Energy?'])
def test_discussion(stores,question):
    svc,calls=service(stores,[partial(60),'I would test a leaner support package.'])
    first=request(svc,None,QUESTION);key=first['conversation_id']
    artifact=deepcopy(svc.conversations.get(key)['artifacts']['generated_deck'])
    result=request(svc,key,question)
    assert result['status']=='answered',result
    assert calls[-1]['current_generated_deck']['id']==artifact['id']
    assert result['answer']['paragraphs'] and 'missing_artifact' not in result['answer']['notices']
    assert not result['envelope']['proof_requested']
    assert svc.conversations.get(key)['artifacts']['generated_deck']==artifact


@pytest.mark.parametrize('phrase',['Make those changes.','Do that.','Try that.','Apply your recommendations.','Show me the updated list.','Make those changes and show me the updated complete 60-card list.'])
def test_apply_chain(stores,phrase):
    active(stores,[('qa-energy',60)])
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    svc,calls=service(stores,[partial(60),changes])
    first=request(svc,None,QUESTION);key=first['conversation_id']
    proposed=request(svc,key,'What exact changes would you make?',include_deck=True,revision=7)
    assert proposed['status']=='answered',proposed
    visible='\n'.join(p['text'] for p in proposed['answer']['paragraphs'])
    assert 'Cut: 1 × Lightning Energy' in visible and 'Add: 1 × Recovery Tool' in visible
    history=svc.conversations.get(key);change=history['artifacts']['proposed_change_set']
    assert change['status']=='PROPOSED' and change['source_artifact_id']==first['answer']['artifact_id']
    assert history['artifacts']['generated_deck']['id']==first['answer']['artifact_id']
    applied=request(svc,key,phrase)
    assert applied['execution']['provider_called'] is False and len(calls)==2
    report=applied['answer']['proposal']
    assert report['validation_status']=='VALIDATED' and report['total_cards']==60
    assert {r['canonical_name']:r['quantity'] for r in report['cards']}=={'Pikachu ex':3,'Recovery Tool':4,'Lightning Energy':53}
    assert applied['answer']['artifact_id']!=first['answer']['artifact_id']
    recounted=request(svc,key,'Recount that deck.')
    assert recounted['answer']['artifact_id']==applied['answer']['artifact_id'] and len(calls)==2
    repeat=request(svc,key,'Do that.')
    assert 'proposal' not in repeat['answer'] and len(calls)==2
    assert before=={k:p.read_bytes() for k,p in stores.paths.items()}


def test_stale_and_ambiguous(stores):
    svc,calls=service(stores,[partial(60),changes,partial(60,pika=4)])
    first=request(svc,None,QUESTION);key=first['conversation_id']
    request(svc,key,'Give me exact changes.')
    proposal=deepcopy(svc.conversations.get(key)['artifacts']['proposed_change_set'])
    request(svc,key,'Create another complete legal 60-card Standard deck with Pikachu ex.')
    result=request(svc,key,'Do that.')
    assert 'older deck' in result['answer']['paragraphs'][0]['text'] and len(calls)==3
    svc.conversations.get(key)['artifacts']['proposed_change_set']=[proposal,deepcopy(proposal)]
    result=request(svc,key,'Do that.')
    assert 'Which proposed' in result['answer']['paragraphs'][0]['text'] and len(calls)==3


@pytest.mark.parametrize('reply',[lambda e:changes(e,2),'I would keep testing recovery.',
    lambda e:'Consider recovery. <POKELAB_ACTIONS>'+json.dumps(dict(type='proposed_deck_changes',changes=[dict(action='remove',**addition(e,'ACE Draw',1)),dict(action='add',**addition(e,'Recovery Tool',1))]))+'</POKELAB_ACTIONS>'])
def test_invalid_or_missing_changes_cannot_apply(stores,reply):
    svc,calls=service(stores,[partial(60),reply])
    first=request(svc,None,QUESTION);key=first['conversation_id']
    request(svc,key,'What exact changes would you make?')
    result=request(svc,key,'Make those changes.')
    assert 'proposal' not in result['answer'] and len(calls)==2
    assert svc.conversations.get(key)['artifacts']['generated_deck']['id']==first['answer']['artifact_id']


def test_evidence_and_identity_labels(stores):
    svc,calls=service(stores,[partial(60),'I would test this recovery plan.'])
    first=request(svc,None,QUESTION)
    result=request(svc,first['conversation_id'],'Show me the evidence for that.')
    assert result['envelope']['proof_requested'] and result['envelope']['evidence']
    env=dict(evidence=[dict(id='card-abc',title='Glass Trumpet',printing='fixture')])
    assert clean_references('Grand Trumpet [card-abc] supports this plan. [fact_ids: card-abc]',env)=='Glass Trumpet supports this plan.'
    assert clean_references('Dragapult ex [card-unknown] is an option.',env)=='Dragapult ex is an option.'


@pytest.mark.parametrize('succeed',[True,False])
def test_small_delta_after_apply(stores,succeed):
    from test_agent_deck_completion import delta
    def cut(env):
        return 'Test a leaner Energy package. <POKELAB_ACTIONS>'+json.dumps(dict(type='proposed_deck_changes',changes=[dict(action='remove',**addition(env,'Lightning Energy',2))]))+'</POKELAB_ACTIONS>'
    svc,calls=service(stores,[partial(60),cut,lambda e:delta([addition(e,'Recovery Tool',1),addition(e,'Lightning Energy',1 if succeed else 2)])])
    first=request(svc,None,QUESTION);key=first['conversation_id']
    request(svc,key,'What exact changes would you make?')
    result=request(svc,key,'Make those changes.')
    assert len(calls)==3
    current=svc.conversations.get(key)['artifacts']['generated_deck']
    assert current['report']['total_cards']==60
    assert (current['id']!=first['answer']['artifact_id'])==succeed


def test_new_recommendation_supersedes_and_explicit_context_switch(stores):
    svc,calls=service(stores,[partial(60),changes,'I would keep testing the active deck.'])
    first=request(svc,None,QUESTION);key=first['conversation_id']
    request(svc,key,'Give me exact changes.')
    request(svc,key,'What exact changes would you make?')
    assert 'proposed_change_set' not in svc.conversations.get(key)['artifacts']
    request(svc,key,'Discuss the active deck.')
    from pokelab.agent_generated_changes import intent
    assert intent('What exact changes would you make?',svc.conversations.get(key)) is None
    assert intent('Critique your own deck.',svc.conversations.get(key))=='DISCUSS'
