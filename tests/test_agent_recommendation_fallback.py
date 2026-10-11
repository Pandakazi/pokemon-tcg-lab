"""Exact PM Gengar shape and classified recovery, all provider calls mocked."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from test_agent_build_routing import stores,sources,setup,research,offline,install,service,ask,custom,novel,quality,cohort
from test_agent_novice_core import state
from test_agent_exact_recommendations import exact
from pokelab.agent_recommendation_fallback import assessment,retry_context,local_options,ratio_option
from pokelab.agent_context_sources import Sources
from pokelab.agent_research import ResearchRequest

FIXTURE=json.loads((Path(__file__).parent/'fixtures/gengar_pm_fallback.json').read_text(encoding='utf-8'))


def pm_seed(svc,stores):
    from pokelab.agent_deck_sandbox import legal_pool
    from pokelab.agent_deck_proposals import Proposal,Candidate,evaluate
    from pokelab.agent_context_sources import stamp
    from pokelab.agent_artifacts import remember,recount
    from pokelab.engine import normalized_name
    from pokelab.rules.models import digest
    fixture_ids={r['id'] for r in FIXTURE['records']}
    pool=[r for r in legal_pool(stores.paths['cards']) if r['card']['id'] in fixture_ids or r['functional_id'].startswith('deck-basic-energy:')];candidates=[]
    for r in pool:
        raw=r['card'];key=r['functional_id']
        candidates.append(dict(candidate_id=key,printing_id=r['printing_id'],role='existing-concept',
            requested_core=raw['name']=='Mega Gengar ex',ace_spec='ACE SPEC' in raw.get('rarity','').upper(),
            basic_energy=key.startswith('deck-basic-energy:'),copy_limit_name=normalized_name(raw['name']),
            **{k:raw[k] for k in ('name','category','stage','evolveFrom','types','attacks','abilities','effect','rules') if k in raw}))
    byid={r['candidate_id']:r for r in candidates}
    selections=[]
    for c in FIXTURE['deck']:
        row=byid.get(c['candidate_id']) or next(r for r in candidates if r['printing_id']==c['printing_id'])
        selections.append(Candidate(candidate_id=row['candidate_id'],quantity=c['quantity']))
    env=dict(lifecycle='FINALIZE',candidate_sandbox=dict(candidates=candidates,consensus=None,limitations=[]),evidence=[],card_source_stamp=digest(stamp(stores.paths['cards'])),build_constraints=dict(format='standard'))
    report,_,_=evaluate(Proposal(kind='list',name='Mega Gengar ex Control',cards=tuple(selections)),(),Sources(**stores.paths),ResearchRequest(scope='conversation',question='Build'),env)
    assert report['validation_status']=='VALIDATED',report['hard_validation']
    report.update(build_mode='custom',generation_source='custom_model_build')
    env['content_hash']=digest(env);artifacts=remember(dict(artifacts={},turn_number=0),report,env)
    key=svc.conversations.put(None,[],[],artifacts=artifacts)
    return dict(conversation_id=key,answer=recount(dict(artifacts=artifacts),'generated_deck'))


def packet(e,cut,add,n=1):
    rows=e['candidate_sandbox']['candidates'];current=e['current_generated_deck']
    return json.dumps(dict(source_artifact_id=current['id'],source_artifact_hash=current['artifact_hash'],
        cuts=[dict(candidate_id=next(r['candidate_id'] for r in rows if r['name']==cut),quantity=n)],
        adds=[dict(candidate_id=next(r['candidate_id'] for r in rows if r['name']==add),quantity=n)]))


@pytest.fixture
def pm(stores):
    import sqlite3
    from tcg_lab.card_db import SQLiteCards
    cards=SQLiteCards(stores.paths['cards'])
    for raw in FIXTURE['records']:cards.put(dict(set={'id':'pm'},localId=raw['id'],**raw))
    with sqlite3.connect(stores.paths['cards']) as db:db.executemany("UPDATE cards SET game='tcg' WHERE id=?",[(r['id'],) for r in FIXTURE['records']])
    return stores


def test_exact_pm_gengar_copy_limit_fallback_and_apply(pm):
    bad=lambda e:packet(e,'Special Red Card','Ultra Ball',2)
    svc,calls=service(pm,[bad,bad]);first=pm_seed(svc,pm)
    original=deepcopy(state(svc,first)['generated_deck'])
    assert original['report']['validation_status']=='VALIDATED' and original['report']['category_subtotals']==dict(Pokemon=12,Trainer=36,Energy=12)
    r=ask(svc,'What exact changes would you make?',first['conversation_id']);diag=r['proposal_attempt']
    assert diag['attempts'][0]['failure_reason']=='copy_limit_violation'
    assert diag['attempts'][0]['retry_strategy']=='retrieve_alternatives_below_copy_limit'
    retry=calls[1]['recommendation_retry'];blocked=diag['attempts'][0]['blocked_candidate_ids']
    assert blocked and not set(blocked)&set(retry['eligible_add_candidate_ids'])
    assert calls[0].get('recommendation_retry') is None and retry['strategy']
    from pokelab.rules.models import digest
    assert calls[1]['content_hash']==digest({k:v for k,v in calls[1].items() if k!='content_hash'})
    assert diag['final_status']=='FALLBACK_VALIDATED' and diag['attempts'][-1]['retry_strategy']=='legal_same_role_replacement'
    pending=state(svc,r)['proposed_change_set'];assert pending['validation_status']=='VALIDATED'
    assert state(svc,r)['generated_deck']==original
    names={r['candidate_id']:r['name'] for r in r['envelope']['candidate_sandbox']['candidates']}
    visible='\n'.join(p['text'] for p in r['answer']['paragraphs'])
    for group,label in [('cuts','Cut'),('adds','Add')]:
        for c in pending[group]:assert f"{label}: {c['quantity']} × {names[c['candidate_id']]}" in visible
    result=ask(svc,'Make those changes',first['conversation_id'])
    assert result['answer'],result
    assert result['answer'].get('proposal'),result['answer']
    assert result['answer']['proposal']['total_cards']==60 and result['answer']['proposal']['validation_status']=='VALIDATED'
    assert ask(svc,'Recount that deck',first['conversation_id'])['answer']['artifact_id']==result['answer']['artifact_id'] and len(calls)==2
    assert svc.conversations.get(first['conversation_id'])['proposal_attempt']==diag


def test_pm_live_successful_swap_offline_regression(pm):
    svc,calls=service(pm,[lambda e:packet(e,'Special Red Card','Spiky Energy',2)])
    first=pm_seed(svc,pm);r=ask(svc,'What exact changes would you make?',first['conversation_id'])
    assert r['proposal_attempt']['final_status']=='MODEL_VALIDATED' and len(calls)==1
    assert 'Add: 2 × Spiky Energy' in '\n'.join(p['text'] for p in r['answer']['paragraphs'])


@pytest.mark.parametrize('reason',['ace_spec_violation','stale_source_artifact','proposal_contract_invalid','candidate_outside_sandbox','no_valid_balanced_swap'])
def test_diagnostic_reasons_change_retry(pm,reason):
    def bad(e):
        if reason=='proposal_contract_invalid':return '{broken'
        v=json.loads(packet(e,'Special Red Card','Poké Pad'))
        if reason=='stale_source_artifact':v['source_artifact_hash']='0'*64
        if reason=='candidate_outside_sandbox':v['adds'][0]['candidate_id']='gameplay:outside'
        if reason=='no_valid_balanced_swap':v['cuts'][0]['quantity']=2
        if reason=='ace_spec_violation':v=json.loads(packet(e,'Special Red Card','Secret Box'))
        return json.dumps(v)
    svc,calls=service(pm,[bad,lambda e:packet(e,'Special Red Card','Poké Pad')])
    first=pm_seed(svc,pm);r=ask(svc,'Recommend exact changes',first['conversation_id'])
    detail=r['proposal_attempt']['attempts'][0]
    assert detail['failure_reason']==reason and detail['retry_strategy']
    assert 'proposed_change_set' in state(svc,r)
    if reason=='proposal_contract_invalid':
        assert detail['retry_strategy']=='repair_structured_contract' and calls[0]['candidate_sandbox']==calls[1]['candidate_sandbox']
    if reason=='ace_spec_violation':
        retry=calls[1];eligible=set(retry['recommendation_retry']['eligible_add_candidate_ids'])
        assert not any(c['candidate_id'] in eligible for c in retry['candidate_sandbox']['candidates'] if c['ace_spec'])


def test_honest_no_material_improvement_has_no_fake_proposal(pm):
    def no_change(e):
        c=e['current_generated_deck'];return json.dumps(dict(source_artifact_id=c['id'],source_artifact_hash=c['artifact_hash'],no_material_improvement=True))
    svc,calls=service(pm,[no_change]);first=pm_seed(svc,pm);before=deepcopy(state(svc,first))
    r=ask(svc,'Recommend exact changes',first['conversation_id'])
    assert r['proposal_attempt']['final_status']=='NO_MATERIAL_IMPROVEMENT' and len(calls)==1
    assert state(svc,r)==before and 'proposed_change_set' not in state(svc,r)
    assert 'meaningful legal upgrade' in r['answer']['paragraphs'][0]['text']


def test_adjacent_role_when_exact_role_options_exhausted(pm):
    svc,calls=service(pm,[lambda e:packet(e,'Special Red Card','Ultra Ball')])
    first=pm_seed(svc,pm);source=state(svc,first)['generated_deck']
    # Get a normal complete packet, then remove exact search role from spare options.
    from pokelab.agent_conversation import context
    request=ResearchRequest(scope='conversation',question='Recommend exact changes')
    env=context(request,Sources(**pm.paths),svc.conversations.get(first['conversation_id']))
    attempted=packet(env,'Special Red Card','Ultra Ball');proposal,_,detail=assessment(attempted,source,env,Sources(**pm.paths),request)
    for r in env['candidate_sandbox']['candidates']:
        if r['name']!='Ultra Ball':r['strategic_roles']=[role for role in r['strategic_roles'] if role!='setup-search']
    options=local_options(source,env,Sources(**pm.paths),request,proposal)
    assert options and options[0][2]=='legal_adjacent_role_replacement'


@pytest.mark.parametrize('prefix',['Your','The','Our','Using'])
def test_successful_explanation_prefix_is_not_an_unresolved_card(novel,prefix):
    svc,calls=service(novel,[custom,f'{prefix} Pikachu ex uses Spark. I would preserve the core.'])
    first=ask(svc,'Make me a Pikachu deck');before=deepcopy(state(svc,first))
    r=ask(svc,'Why did you choose these cards?',first['conversation_id'])
    assert 'printed_fact_review' not in r['answer']['notices'] and state(svc,r)==before
    assert r['answer']['fact_reviews'] and all(f['status']=='printed_reference' for f in r['answer']['fact_reviews'])
    assert not r['envelope']['proof_requested']


def test_real_unresolved_detail_still_warns(novel):
    svc,calls=service(novel,[custom,'Unknownmon uses Fake Storm. Keep the core.']);first=ask(svc,'Make me a Pikachu deck')
    r=ask(svc,'Explain this deck',first['conversation_id']);assert 'printed_fact_review' in r['answer']['notices']


def test_safe_current_ratio_is_validated_and_can_exhaust(pm):
    from pokelab.agent_deck_proposals import Candidate,Proposal,evaluate
    from pokelab.agent_generated_changes import compose
    from pokelab.agent_conversation import context
    svc,_=service(pm,[]);first=pm_seed(svc,pm);source=deepcopy(state(svc,first)['generated_deck'])
    request=ResearchRequest(scope='conversation',question='Recommend exact changes')
    env=context(request,Sources(**pm.paths),svc.conversations.get(first['conversation_id']))
    rows=env['candidate_sandbox']['candidates'];ids={r['name']:r['candidate_id'] for r in rows}
    diff=Proposal(kind='diff',removes=(Candidate(candidate_id=ids['Poké Pad'],quantity=1),),adds=(Candidate(candidate_id=ids['Handheld Fan'],quantity=1),))
    report,_,_=evaluate(compose(source,diff,env['candidate_sandbox']),(),Sources(**pm.paths),request,env)
    assert report['validation_status']=='VALIDATED';source['report']=report
    for row in rows:row['strategic_roles']=['setup-search'] if row['name']=='Poké Pad' else []
    option=ratio_option(source,env,Sources(**pm.paths),request)
    assert option and option[2]=='safe_current_consistency_adjustment'
    assert option[1]['total_cards']==60 and option[1]['validation_status']=='VALIDATED'
    for row in rows:row['strategic_roles']=[]
    assert ratio_option(source,env,Sources(**pm.paths),request) is None


def test_trimmed_required_candidate_is_restored(pm):
    from pokelab.agent_conversation import context
    svc,_=service(pm,[]);first=pm_seed(svc,pm);source=state(svc,first)['generated_deck']
    request=ResearchRequest(scope='conversation',question='Recommend exact changes')
    env=context(request,Sources(**pm.paths),svc.conversations.get(first['conversation_id']))
    text=packet(env,'Special Red Card','Spiky Energy')
    key=json.loads(text)['adds'][0]['candidate_id']
    env['required_replacement_candidate_ids']=[key]
    env['candidate_sandbox']['candidates']=[r for r in env['candidate_sandbox']['candidates'] if r['candidate_id']!=key]
    proposal,_,detail=assessment(text,source,env,Sources(**pm.paths),request)
    assert detail['failure_reason']=='context_budget_trimmed_required_candidates'
    retry=retry_context(source,env,Sources(**pm.paths),detail,proposal)
    assert key in {r['candidate_id'] for r in retry['candidate_sandbox']['candidates']}
    assert detail['retry_strategy']=='restore_required_candidates'


@pytest.mark.parametrize('question',['Build me a Dragapult deck','Build me Lopunny Dusknoir'])
def test_consensus_exact_change_apply_recount(cohort,question):
    from test_agent_build_routing import explicit
    if 'Lopunny' in question:explicit(cohort)
    def reply(env):
        current=env['current_generated_deck']
        energy=[r for r in current['cards'] if r['candidate_id'].startswith('deck-basic-energy:')]
        return json.dumps(dict(source_artifact_id=current['id'],source_artifact_hash=current['artifact_hash'],
            cuts=[dict(candidate_id=energy[0]['candidate_id'],quantity=1)],
            adds=[dict(candidate_id=energy[1]['candidate_id'],quantity=1)]))
    svc,calls=service(cohort,[reply]);first=ask(svc,question);key=first['conversation_id']
    original=deepcopy(state(svc,first)['generated_deck'])
    assert 'consensus' in original['report']['generation_source']
    recommended=ask(svc,'What exact changes would you make?',key)
    assert recommended['proposal_attempt']['final_status']=='MODEL_VALIDATED'
    assert state(svc,recommended)['generated_deck']==original
    applied=ask(svc,'Make those changes',key)
    assert applied['answer']['proposal']['validation_status']=='VALIDATED' and applied['answer']['proposal']['total_cards']==60
    recounted=ask(svc,'Recount that deck',key)
    assert recounted['answer']['artifact_id']==applied['answer']['artifact_id'] and len(calls)==1
