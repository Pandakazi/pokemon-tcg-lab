"""Presentation-only functional disambiguation plus the real apply boundary."""
from copy import deepcopy
import json
import pytest
from pokelab.agent_change_labels import change_lines
from test_agent_recommendation_fallback import pm,pm_seed,stores,sources,setup,research,offline,quality,cohort,novel
from test_agent_build_routing import install,service,ask
from test_agent_novice_core import state


def row(key,printing,name='Gastly',attacks=(),abilities=()):
    return dict(candidate_id=key,printing_id=printing,canonical_name=name,
        printed=dict(attacks=[dict(name=n) for n in attacks],abilities=[dict(name=n) for n in abilities]))


def proposal(cut='gameplay:old',add='gameplay:new'):
    return dict(removes=[dict(candidate_id=cut,quantity=1)],adds=[dict(candidate_id=add,quantity=1)])


@pytest.mark.parametrize('field,kind',[('attacks','Attack'),('abilities','Ability')])
def test_distinctive_gameplay_names_and_immutable_inputs(field,kind):
    a=row('gameplay:old','sv05-102',**{field:['Old move']})
    b=row('gameplay:new','me03-048',**{field:['New move']})
    p=proposal();before=deepcopy((p,a,b))
    assert change_lines(p,[a],[b])==[f'Cut: 1 × Gastly — {kind}: Old move',f'Add: 1 × Gastly — {kind}: New move']
    assert (p,a,b)==before


def test_ability_precedes_attack_and_shared_features_do_not_distinguish():
    a=row('gameplay:old','sv05-102',attacks=['Shared','Old attack'],abilities=['Old ability'])
    b=row('gameplay:new','me03-048',attacks=['Shared','New attack'],abilities=['New ability'])
    assert change_lines(proposal(),[a],[b])==['Cut: 1 × Gastly — Ability: Old ability','Add: 1 × Gastly — Ability: New ability']
    a['printed']['abilities']=[];b['printed']['abilities']=[]
    assert change_lines(proposal(),[a],[b])==['Cut: 1 × Gastly — Attack: Old attack','Add: 1 × Gastly — Attack: New attack']


@pytest.mark.parametrize('attacks',[[],['Shared attack'],['Very long attack '*8]])
def test_public_printing_fallback_without_internal_ids(attacks):
    a=row('gameplay:old','sv05-102',attacks=attacks)
    b=row('gameplay:new','me03-048',attacks=attacks)
    lines=change_lines(proposal(),[a],[b])
    assert lines==['Cut: 1 × Gastly (sv05-102)','Add: 1 × Gastly (me03-048)']
    assert 'gameplay:' not in '\n'.join(lines)


def test_same_functional_identity_different_printing_stays_simple():
    a=row('gameplay:same','sv05-102',attacks=['Same attack'])
    b=row('gameplay:same','me03-048',attacks=['Same attack'])
    assert change_lines(proposal('gameplay:same','gameplay:same'),[a],[b])==['Cut: 1 × Gastly','Add: 1 × Gastly']


def test_unique_names_stay_simple():
    a=row('gameplay:old','tk-bw-z-3',name='Darkness Energy')
    b=row('gameplay:new','sv06-150',name='Handheld Fan')
    assert change_lines(proposal(),[a],[b])==['Cut: 1 × Darkness Energy','Add: 1 × Handheld Fan']


def test_fully_removed_card_uses_retained_candidate_facts_without_mutation():
    a=row('gameplay:old','sv05-102');a.pop('printed')
    b=row('gameplay:new','me03-048',attacks=['New attack'])
    candidates=[dict(candidate_id='gameplay:old',attacks=[dict(name='Old attack')])]
    before=deepcopy((a,b,candidates))
    assert change_lines(proposal(),[a],[b],candidates)==['Cut: 1 × Gastly — Attack: Old attack','Add: 1 × Gastly — Attack: New attack']
    assert (a,b,candidates)==before


def test_validated_same_name_swap_applies_exact_identity_and_recounts(pm):
    # Synthetic legal second Gastly: recommendation selection remains provider-owned.
    install(pm,[dict(id='me03-048',name='Gastly',category='Pokemon',stage='Basic',types=['Darkness'],
        hp=60,attacks=[dict(name='Distinct test attack',cost=['Darkness'],damage=10)],
        regulationMark='H',legal={'standard':True},variants={'normal':True})])
    captured=[]
    def reply(env):
        current=env['current_generated_deck'];rows=env['candidate_sandbox']['candidates']
        cut=next(r for r in current['cards'] if r['canonical_name']=='Gastly')
        add=next(r for r in rows if r['printing_id']=='me03-048')
        value=dict(source_artifact_id=current['id'],source_artifact_hash=current['artifact_hash'],
            cuts=[dict(candidate_id=cut['candidate_id'],quantity=1)],adds=[dict(candidate_id=add['candidate_id'],quantity=1)])
        captured.append(deepcopy(value));return json.dumps(value)
    svc,calls=service(pm,[reply]);first=pm_seed(svc,pm);key=first['conversation_id']
    original=deepcopy(state(svc,first)['generated_deck'])
    recommended=ask(svc,'What exact changes would you make?',key)
    pending=state(svc,recommended)['proposed_change_set']
    assert pending['validation_status']=='VALIDATED' and state(svc,recommended)['generated_deck']==original
    assert pending['cuts']==captured[0]['cuts'] and pending['adds']==captured[0]['adds']
    text='\n'.join(p['text'] for p in recommended['answer']['paragraphs'])
    assert 'Cut: 1 × Gastly — ' in text and 'Add: 1 × Gastly — Attack: Distinct test attack' in text
    assert 'gameplay:' not in text and all(c['candidate_id'] not in text for c in pending['cuts']+pending['adds'])
    applied=ask(svc,'Make those changes',key);report=applied['answer']['proposal']
    counts={r['candidate_id']:r['quantity'] for r in report['cards']}
    assert counts[pending['cuts'][0]['candidate_id']]==3 and counts[pending['adds'][0]['candidate_id']]==1
    assert report['validation_status']=='VALIDATED' and report['total_cards']==60
    recounted=ask(svc,'Recount that deck',key)
    assert recounted['answer']['proposal']['cards']==report['cards'] and len(calls)==1
