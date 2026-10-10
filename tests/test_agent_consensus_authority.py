"""Consensus is authoritative; provider discussion cannot mutate artifacts."""
from copy import deepcopy
import json
import pytest
from pokelab.agent_research import ResearchRequest
from pokelab.agent_artifacts import remember
from test_agent_consensus import cohort,quality,stores,sources,setup,research,offline
from test_agent_deck_completion import service

QUESTION='Create me a complete legal 60-card Dragapult ex deck and put it in list form. Make every slot an exact card, include category subtotals, and make sure the total is exactly 60.'


def ask(svc,q,key=None):return svc.run(ResearchRequest(scope='conversation',question=q,conversation_id=key))


def test_pm_verbose_build_is_exact_consensus_without_provider(cohort):
    svc,calls=service(cohort,['must never be used'])
    r=ask(svc,QUESTION);report=r['answer']['proposal'];c=r['envelope']['candidate_sandbox']['consensus']
    assert r['status']=='answered' and not calls
    assert report['generation_source']=='recent_consensus' and report['consensus_status']=='complete'
    assert {x['candidate_id']:x['quantity'] for x in report['cards']}=={x['candidate_id']:x['quantity'] for x in c['cards']}
    assert report['total_cards']==60 and report['validation_status']=='VALIDATED'


@pytest.mark.parametrize('question',[
    'Why did you choose these cards?', 'Why is there SO MUCH energy in the deck? Most lists only run 9 at most',
    'Critique this deck.', 'Explain the game plan.', 'What are the weak points?',
    'How does this matchup work?', 'Why does this complete 60-card list work?'])
def test_read_turn_ignores_malicious_replacement_and_recounts(cohort,question):
    reply='I would test the setup plan. <POKELAB_ACTIONS>'+json.dumps(dict(type='generated_deck',cards=[dict(card_name='Missing Card',quantity=60)]))+'</POKELAB_ACTIONS>'
    svc,calls=service(cohort,[reply]);first=ask(svc,QUESTION);key=first['conversation_id']
    before=deepcopy(svc.conversations.get(key)['artifacts'])
    r=ask(svc,question,key)
    assert r['status']=='answered',r
    assert r['envelope']['artifact_mutation_allowed'] is False
    assert r['envelope']['current_generated_deck']['id']==before['generated_deck']['id']
    assert 'proposal' not in r['answer'] and 'read_only_artifact_ignored' in r['answer']['action_diagnostics']
    assert svc.conversations.get(key)['artifacts']==before
    assert 'printed_fact_review' not in r['answer']['notices']
    recount=ask(svc,'Recount that deck.',key)
    assert recount['answer']['artifact_id']==before['generated_deck']['id'] and recount['answer']['proposal']['total_cards']==60
    assert len(calls)==1


def test_deviation_question_local_truth_and_evidence_on_demand(cohort):
    svc,calls=service(cohort,['The current shell is a reasonable starting point.'])
    first=ask(svc,QUESTION);key=first['conversation_id'];before=deepcopy(svc.conversations.get(key)['artifacts'])
    r=ask(svc,'Why did you deviate from recent consensus?',key)
    assert 'did not' in r['answer']['paragraphs'][0]['text'] and not calls
    assert svc.conversations.get(key)['artifacts']==before
    proof=ask(svc,'Show me the competitive data behind this.',key)
    assert proof['envelope']['proof_requested'] and proof['envelope']['evidence']
    assert svc.conversations.get(key)['artifacts']==before


def test_known_current_cards_cannot_be_reported_unavailable(cohort):
    svc,calls=service(cohort,['Dragapult ex and Drakloak are unavailable in the sandbox. This deck is a placeholder list. I would test its setup consistency.'])
    first=ask(svc,QUESTION);r=ask(svc,'Why so much Energy?',first['conversation_id'])
    prose=' '.join(x['text'] for x in r['answer']['paragraphs'])
    assert 'unavailable' not in prose and 'placeholder' not in prose
    assert 'authoritative' in prose and 'setup consistency' in prose


def test_storage_boundary_refuses_direct_readonly_overwrite():
    history={'artifacts':{'generated_deck':{'id':'original'}}}
    assert remember(history,dict(kind='list'),dict(artifact_mutation_allowed=False))==history['artifacts']
    from pokelab.agent_artifacts import pending_repair
    history['artifacts']['generated_deck']['pending']=True
    assert pending_repair('Critique this complete deck.',history) is None


def test_unknown_generic_never_silently_invents(stores):
    svc,calls=service(stores,['must not run']);r=ask(svc,'Build me an UnknownArchetype deck')
    assert not calls and 'proposal' not in r['answer']
    assert r['envelope']['generation']['consensus_status']=='unknown_archetype'
    assert r['envelope']['generation']['generation_source'] is None
    verbose=ask(svc,QUESTION)
    assert not calls and verbose['envelope']['generation']['consensus_status']=='unknown_archetype'


def test_insufficient_and_invalid_consensus_fallback_is_explicit(cohort,monkeypatch):
    import sqlite3
    import pokelab.agent_deck_proposals as proposals
    svc,calls=service(cohort,['I would test a custom setup; no established baseline is available.'])
    monkeypatch.setattr(proposals,'evaluate',lambda *args,**kwargs:(dict(validation_status='INVALID'),[],set()))
    r=ask(svc,QUESTION)
    assert len(calls)==1 and r['envelope']['generation']['fallback_reason']=='invalid' and 'proposal' not in r['answer']
    assert r['envelope']['generation']['generation_source']=='custom_model_build'
    with sqlite3.connect(cohort.paths['competitive']) as db:db.execute('DELETE FROM competitive_decks WHERE rank>2')
    r=ask(svc,QUESTION)
    assert len(calls)==2 and r['envelope']['generation']['fallback_reason']=='insufficient_sample'


def test_explicit_modify_keeps_proposal_path(cohort):
    def reply(e):
        rows=e['current_generated_deck']['cards'];energy=next(r for r in rows if r['candidate_id'].startswith('deck-basic-energy:'))
        return 'I would test a different Energy balance. <POKELAB_ACTIONS>'+json.dumps(dict(type='proposed_deck_changes',changes=[dict(action='remove',candidate_id=energy['candidate_id'],quantity=1),dict(action='add',candidate_id=next(r['candidate_id'] for r in rows if r['candidate_id'].startswith('deck-basic-energy:') and r!=energy),quantity=1)],rationale='Test the balance.'))+'</POKELAB_ACTIONS>'
    svc,calls=service(cohort,[reply]);first=ask(svc,QUESTION);key=first['conversation_id']
    r=ask(svc,'Make this more aggressive.',key)
    assert r['envelope']['generated_intent']=='RECOMMEND' and len(calls)==1
    assert svc.conversations.get(key)['artifacts']['proposed_change_set']['status']=='PROPOSED'
    applied=ask(svc,'Make those changes.',key)
    assert applied['answer']['artifact_id']!=first['answer']['artifact_id'] and len(calls)==1
