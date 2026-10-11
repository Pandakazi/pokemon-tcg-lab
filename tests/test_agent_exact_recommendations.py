"""PM custom build -> exact proposal -> apply -> recount, offline real validation."""
from copy import deepcopy
import json
import pytest
from test_agent_build_routing import novel,quality,stores,sources,setup,research,offline,cohort,install,service,custom,ask
from test_agent_novice_core import pokemon,state
from pokelab.agent_generated_changes import source_hash,structured


def exact(e):
    current=e['current_generated_deck'];counts={r['candidate_id']:r['quantity'] for r in current['cards']}
    # A spare legal Trainer slot; never cut the build-around to force a tradeoff.
    cut=next(r for r in e['candidate_sandbox']['candidates'] if r['basic_energy'] and counts.get(r['candidate_id'],0)>1)
    add=next(r for r in e['candidate_sandbox']['candidates'] if r['category']=='Trainer' and not r['ace_spec'] and counts.get(r['candidate_id'],0)<4)
    return json.dumps(dict(source_artifact_id=current['id'],source_artifact_hash=current['artifact_hash'],
        cuts=[dict(candidate_id=cut['candidate_id'],quantity=1)],adds=[dict(candidate_id=add['candidate_id'],quantity=1)]))


@pytest.mark.parametrize('theme',['Pikachu','Gengar'])
@pytest.mark.parametrize('question',['What exact changes would you make?','Recommend exact changes.','What should I cut and add?'])
def test_pm_custom_loop(novel,theme,question):
    if theme=='Gengar':install(novel,[pokemon('pm-mega-gengar','Mega Gengar ex')])
    svc,calls=service(novel,[custom,exact]);before={k:p.read_bytes() for k,p in novel.paths.items()}
    first=ask(svc,f'Make me a {theme} deck');key=first['conversation_id']
    original=deepcopy(state(svc,first)['generated_deck'])
    assert original['report']['total_cards']==60 and original['report']['build_mode']=='custom'
    proposed=ask(svc,question,key);pending=state(svc,proposed)['proposed_change_set']
    assert pending['source_artifact_id']==original['id'] and pending['source_artifact_hash']==source_hash(original)
    assert pending['validation_status']=='VALIDATED' and pending['cuts'] and pending['adds']
    assert state(svc,proposed)['generated_deck']==original
    names={r['candidate_id']:r['name'] for r in calls[-1]['candidate_sandbox']['candidates']}
    visible='\n'.join(r['text'] for r in proposed['answer']['paragraphs'])
    for group,label in [('cuts','Cut'),('adds','Add')]:
        for c in pending[group]:assert f"{label}: {c['quantity']} × {names[c['candidate_id']]}" in visible
    assert 'Make those changes' in visible and 'No validated exact' not in visible
    assert not proposed['envelope']['proof_requested'] and calls[-1]['candidate_sandbox']['replacement_pool']
    applied=ask(svc,'Make those changes',key);report=applied['answer']['proposal']
    assert report['total_cards']==60 and report['validation_status']=='VALIDATED'
    expected={r['candidate_id']:r['quantity'] for r in original['report']['cards']}
    for c in pending['cuts']:expected[c['candidate_id']]-=c['quantity']
    for c in pending['adds']:expected[c['candidate_id']]=expected.get(c['candidate_id'],0)+c['quantity']
    assert {r['candidate_id']:r['quantity'] for r in report['cards']}=={k:v for k,v in expected.items() if v}
    recount=ask(svc,'Recount that deck',key)
    assert recount['answer']['artifact_id']==applied['answer']['artifact_id'] and recount['answer']['proposal']['cards']==report['cards']
    assert len(calls)==2 and before=={k:p.read_bytes() for k,p in novel.paths.items()}


@pytest.mark.parametrize('failure',['missing','unsupported','stale','copy_limit','unbalanced'])
def test_bounded_retry_selects_legal_alternative_without_rejected_prose(novel,failure):
    def invalid(e):
        if failure=='missing':return 'I recommend Energy Switch, an unavailable conceptual card.'
        value=json.loads(exact(e))
        if failure=='unsupported':value['adds'][0]['candidate_id']='outside-sandbox-energy-switch'
        if failure=='stale':value['source_artifact_hash']='0'*64
        if failure=='copy_limit':
            counts={r['candidate_id']:r['quantity'] for r in e['current_generated_deck']['cards']}
            value['adds'][0]['candidate_id']=next(r['candidate_id'] for r in e['candidate_sandbox']['candidates'] if r['category']=='Trainer' and counts.get(r['candidate_id'])==4)
        if failure=='unbalanced':value['cuts'][0]['quantity']=2
        return json.dumps(value)
    svc,calls=service(novel,[custom,invalid,exact]);first=ask(svc,'Make me a Pikachu deck')
    r=ask(svc,'What exact changes would you make?',first['conversation_id'])
    assert len(calls)==3 and r['execution']['recommendation_repair_calls']==1
    assert 'proposed_change_set' in state(svc,r)
    assert 'Energy Switch' not in '\n'.join(p['text'] for p in r['answer']['paragraphs'])
    assert 'recommendation_retry' in calls[-1] and 'outside-sandbox-energy-switch' not in json.dumps(calls[-1])
    applied=ask(svc,'Make those changes',first['conversation_id'])
    assert applied['answer']['proposal']['total_cards']==60 and len(calls)==3


def test_new_replacement_candidate_retained_for_apply(novel):
    def replacement(e):
        value=json.loads(exact(e));current={r['candidate_id'] for r in e['current_generated_deck']['cards']}
        value['adds'][0]['candidate_id']=next(r['candidate_id'] for r in e['candidate_sandbox']['candidates'] if r['category']=='Trainer' and not r['ace_spec'] and r['candidate_id'] not in current)
        return json.dumps(value)
    svc,calls=service(novel,[custom,replacement]);first=ask(svc,'Make me a Pikachu deck')
    artifact=state(svc,first)['generated_deck'];current={r['candidate_id'] for r in artifact['report']['cards']}
    packet=artifact['report']['candidate_sandbox']
    packet['candidates']=[r for r in packet['candidates'] if r['candidate_id'] in current]
    before=deepcopy(artifact)
    r=ask(svc,'Recommend exact changes',first['conversation_id']);pending=state(svc,r)['proposed_change_set']
    assert pending['replacement_candidates'] and state(svc,r)['generated_deck']==before
    applied=ask(svc,'Make those changes',first['conversation_id'])
    assert applied['answer']['proposal']['validation_status']=='VALIDATED'


def test_legacy_prose_conflict_is_discarded(novel):
    def legacy(e):
        v=json.loads(exact(e))
        return 'Add Energy Switch and remove the core! <POKELAB_ACTIONS>'+json.dumps(dict(type='proposed_deck_changes',changes=[dict(action=a,**r) for a,k in [('remove','cuts'),('add','adds')] for r in v[k]],rationale='Add an unavailable card instead.'))+'</POKELAB_ACTIONS>'
    svc,calls=service(novel,[custom,legacy]);first=ask(svc,'Make me a Pikachu deck')
    r=ask(svc,'Recommend exact changes',first['conversation_id'])
    text='\n'.join(p['text'] for p in r['answer']['paragraphs'])
    assert 'Cut:' in text and 'Add:' in text and 'Energy Switch' not in text and 'unavailable' not in text


def test_failed_retry_preserves_deck_and_explicit_evidence(novel):
    svc,calls=service(novel,[custom,'No structured answer','No structured answer','Here is strategic evidence context.'])
    first=ask(svc,'Make me a Pikachu deck');original=deepcopy(state(svc,first)['generated_deck'])
    r=ask(svc,'What exact changes would you make?',first['conversation_id'])
    assert r['answer']['recommendation_failure']['attempts']==2 and state(svc,r)['generated_deck']==original
    assert 'proposed_change_set' not in state(svc,r)
    r=ask(svc,'Show me the evidence behind those changes',first['conversation_id'])
    assert r['envelope']['proof_requested'] and r['envelope']['evidence']


@pytest.mark.parametrize('value',[True,0,-1,1.5,'1'])
def test_quantity_contract_is_strict(value):
    artifact=dict(id='source',report={})
    packet=dict(source_artifact_id='source',source_artifact_hash=source_hash(artifact),cuts=[dict(candidate_id='a',quantity=value)],adds=[dict(candidate_id='b',quantity=1)])
    with pytest.raises(ValueError):structured(json.dumps(packet),artifact)
