"""Production orchestration with optional pressure and a network-free provider."""
from copy import deepcopy
import json
import pytest
from pokelab.agent_research import ResearchRequest,canonical
from pokelab.agent_context_budget import fit
from pokelab.agent_generated_changes import source_hash
from test_agent_consensus_authority import QUESTION,ask
from test_agent_consensus import cohort,quality,stores,sources,setup,research,offline
from test_agent_deck_completion import service

CHANGES='What exact changes would you make to improve this deck while staying close to the current competitive Dragapult shell? Show me the exact cuts and adds.'


def change_reply(e):
    rows=[r for r in e['current_generated_deck']['cards'] if r['candidate_id'].startswith('deck-basic-energy:')]
    action=dict(type='proposed_deck_changes',changes=[dict(action='remove',candidate_id=rows[0]['candidate_id'],quantity=1),dict(action='add',candidate_id=rows[1]['candidate_id'],quantity=1)],rationale='Test the Energy balance.')
    return 'I would test this Energy balance. <POKELAB_ACTIONS>'+json.dumps(action)+'</POKELAB_ACTIONS>'


def pressure(history):
    packet=history['artifacts']['generated_deck']['report']['candidate_sandbox']
    packet['consensus']['presentation_provenance']='optional '*1500
    for row in packet['candidates']:row['ranking_provenance']='duplicate '*20


def test_pm_exact_change_preserves_task_under_pressure_and_applies(cohort):
    svc,calls=service(cohort,[change_reply,'The shell remains a useful starting point.'])
    initial=ask(svc,QUESTION);key=initial['conversation_id'];history=svc.conversations.get(key)
    pressure(history);before=deepcopy(history['artifacts']);original=before['generated_deck']
    database_before={k:p.read_bytes() for k,p in cohort.paths.items()}
    r=ask(svc,CHANGES,key)
    assert r['status']=='answered' and len(calls)==1,r
    e=calls[0]
    assert len(canonical(e).encode())<=23000
    assert e['context_budget']['before_bytes']>23000
    assert e['question']==CHANGES and e['generated_intent']=='RECOMMEND'
    assert e['build_constraints']==dict(format='standard',target_total=60,all_slots_resolved=True,all_slots_standard_legal=True)
    deck=e['current_generated_deck']
    assert deck['id']==original['id'] and deck['artifact_hash']==source_hash(original)
    assert sum(r['quantity'] for r in deck['cards'])==60
    assert deck['cards']==[{k:r[k] for k in ('candidate_id','canonical_name','printing_id','quantity')} for r in original['report']['cards']]
    assert [r['candidate_id'] for r in e['candidate_sandbox']['candidates']]==[r['candidate_id'] for r in original['report']['candidate_sandbox']['candidates']]
    trims=e['context_budget']['trims']
    assert trims.index('deduplicate_provenance')<trims.index('compact_candidate_support')
    assert 'printed_fact_review' not in r['answer']['notices'] and not r['answer']['facts'] and not e['proof_requested']
    text=' '.join(p['text'] for p in r['answer']['paragraphs'])
    assert 'Cut: 1' in text and 'Add: 1' in text
    retained=svc.conversations.get(key)['artifacts']
    assert retained['generated_deck']==original
    assert retained['proposed_change_set']['status']=='PROPOSED'
    proposal=deepcopy(retained['proposed_change_set'])
    proof=ask(svc,'Show me the evidence behind those changes.',key)
    assert proof['envelope']['proof_requested'] and proof['envelope']['evidence']
    assert calls[1]['pending_changes']==proposal
    assert svc.conversations.get(key)['artifacts']==retained
    applied=ask(svc,'Make those changes.',key)
    assert applied['answer']['proposal']['total_cards']==60 and applied['answer']['proposal']['validation_status']=='VALIDATED'
    assert len(calls)==2  # apply is local, not a provider retry
    assert database_before=={k:p.read_bytes() for k,p in cohort.paths.items()}


@pytest.mark.parametrize('question',[
    'What is the evidence budget?', 'How does the consensus baseline work?',
    'What does validated mean?', 'Why does it say proposal only?',
    'What data are you using?', 'How does the sandbox work?',
    'Why did PokéLab refuse that?'])
def test_meta_route_is_local_readonly_and_has_no_sources(cohort,question,monkeypatch):
    svc,calls=service(cohort,[change_reply]);first=ask(svc,QUESTION);key=first['conversation_id']
    ask(svc,CHANGES,key)
    before=deepcopy(svc.conversations.get(key)['artifacts']);proposal=deepcopy(svc.conversations.get(key)['proposal'])
    import pokelab.agent_conversation as c
    with monkeypatch.context() as patch:
        patch.setattr(c,'context',lambda *a:pytest.fail('meta must not retrieve card/deck context'))
        r=ask(svc,question,key)
    assert r['status']=='answered' and r['execution']==dict(mode='local_system',provider_called=False)
    assert r['envelope']['route']=='system' and r['envelope']['evidence']==[] and not r['envelope']['proof_requested']
    assert r['answer']['facts']==[] and r['answer']['notices']==[] and 'proposal' not in r['answer']
    assert svc.conversations.get(key)['artifacts']==before and svc.conversations.get(key)['proposal']==proposal
    recount=ask(svc,'Recount that deck.',key)
    assert recount['answer']['artifact_id']==before['generated_deck']['id'] and recount['answer']['proposal']['total_cards']==60
    assert len(calls)==1


def test_required_overflow_retains_incident_deck_and_pending_proposal(cohort,monkeypatch):
    svc,calls=service(cohort,[change_reply]);first=ask(svc,QUESTION);key=first['conversation_id']
    ask(svc,CHANGES,key);before=deepcopy(svc.conversations.get(key)['artifacts'])
    import pokelab.agent_conversation as c
    with monkeypatch.context() as patch:
        patch.setattr(c,'CONTEXT_BYTES',1500)
        r=ask(svc,CHANGES,key)
    assert r['status']=='budget_exceeded' and r['context_diagnostics']['condition']=='required_context_overflow'
    assert r['context_diagnostics']['provider_called'] is False and len(calls)==1
    assert svc.conversations.get(key)['artifacts']==before
    incident=ask(svc,'Why did that fail?',key)
    assert 'context budget' in incident['answer']['paragraphs'][0]['text'] and 'before the model' in incident['answer']['paragraphs'][0]['text']
    assert not incident['envelope']['evidence'] and len(calls)==1
    assert svc.conversations.get(key)['artifacts']==before


def test_all_optional_tiers_can_degrade_without_mutating_saved_context(cohort):
    svc,_=service(cohort,[change_reply]);first=ask(svc,QUESTION);key=first['conversation_id']
    from pokelab.agent_conversation import context
    from pokelab.agent_context_sources import Sources
    envelope=context(ResearchRequest(scope='conversation',question=CHANGES),Sources(**cohort.paths),svc.conversations.get(key))
    # Force the floor by huge support fields, but keep current task and IDs small.
    for r in envelope['candidate_sandbox']['candidates']:r['effect']='optional printed '*2000
    envelope['candidate_sandbox']['competitive_prior']={'optional':'x'*30000}
    envelope['evidence'].append(dict(id='extra',kind='evidence',value='x'*30000))
    envelope['history']=[dict(optional='x'*30000)]
    envelope['artifacts']['old']={'optional':'x'*30000}
    before=deepcopy(envelope);compacted=fit(envelope,14000)
    assert envelope==before
    assert compacted['current_generated_deck']==before['current_generated_deck']
    assert compacted['context_budget']['trims']==['deduplicate_provenance','duplicate_generated_artifact','compact_candidate_support','optional_card_evidence','older_conversation','optional_printed_text','optional_competitive_support','other_historical_artifacts']
    assert len(canonical(compacted).encode())<14000
    assert [r['candidate_id'] for r in compacted['candidate_sandbox']['candidates']]==[r['candidate_id'] for r in before['candidate_sandbox']['candidates']]


def test_card_question_containing_sandbox_is_not_system_route(cohort):
    svc,calls=service(cohort,['I would test that option.']);first=ask(svc,QUESTION)
    r=ask(svc,'How does Dragapult work with the sandbox candidates?',first['conversation_id'])
    assert len(calls)==1 and r['envelope'].get('route')!='system'


def test_local_product_question_does_not_require_provider_configuration(stores,monkeypatch):
    svc,calls=service(stores,['must never run'])
    monkeypatch.setattr(svc,'configured',lambda:pytest.fail('local explanation must not configure provider'))
    r=ask(svc,'What is the evidence budget?')
    assert r['status']=='answered' and not calls
    assert '23,000 bytes' in r['answer']['paragraphs'][0]['text']


def test_selected_printing_and_active_snapshot_survive_last_optional_tier():
    selected=dict(printing='selected',variant='holo')
    active=dict(id='active-deck',kind='fact',value=dict(revision=157,entries=[dict(quantity=60)]),content_hash='a'*64)
    card=dict(id='selected-fact',kind='fact',printing='selected',title='Selected card',value=dict(effect='Local printed effect.'))
    e=dict(question=CHANGES,selected=selected,revision=157,window='30',
        build_constraints=dict(format='standard',target_total=60),generated_intent='RECOMMEND',
        current_generated_deck=dict(id='deck',artifact_hash='b'*64,cards=[dict(candidate_id='candidate',quantity=60)]),
        pending_changes=dict(id='pending',source_artifact_id='deck',source_artifact_hash='b'*64,proposal={'adds':[],'removes':[]}),
        candidate_sandbox=dict(candidates=[dict(candidate_id='candidate',printing_id='selected',name='Selected card',category='Energy')],competitive_prior={'support':'x'*10000}),
        artifacts={},history=[],evidence=[active,card,dict(id='optional',kind='evidence',value='x'*10000)])
    result=fit(e,2500)
    assert result['selected']==selected and result['revision']==157 and result['window']=='30'
    assert result['evidence']==[active,card] and result['pending_changes']==e['pending_changes']
    assert result['current_generated_deck']==e['current_generated_deck'] and result['build_constraints']==e['build_constraints']
    assert 'optional_competitive_support' in result['context_budget']['trims']
