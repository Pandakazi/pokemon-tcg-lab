"""New-build isolation, one contract recovery and generic custom shape offline."""
from copy import deepcopy
import json
import httpx
import pytest
from test_agent_build_routing import novel,quality,stores,sources,setup,research,offline,cohort,install,service,custom,ask,actions,change
from test_agent_novice_core import pokemon,state
from pokelab.agent_build_core import new_build


def obj(e,n=60,energy=None):
    value=json.loads(custom(e).split('<POKELAB_ACTIONS>')[1].split('</POKELAB_ACTIONS>')[0])
    value['cards'][-1]['quantity']+=n-60
    if energy is not None:
        keep=value['cards'][0];ener=value['cards'][-1]
        trainers=[r for r in e['candidate_sandbox']['candidates'] if r['category']=='Trainer' and not r['ace_spec']]
        remain=n-keep['quantity']-energy
        rows=[keep]
        for r in trainers:
            take=min(4,remain)
            if take:rows.append(dict(candidate_id=r['candidate_id'],quantity=take));remain-=take
        assert remain==0
        rows.append(dict(ener,quantity=energy));value['cards']=rows
    value['name']='Independent custom build'
    return value


@pytest.mark.parametrize('q',['Add Gengar to this deck','Can we work Gengar into this?','Replace Pikachu with Gengar','Modify this deck around Gengar','Build this around Munkidori','Make this more aggressive','Swap in Mega Lopunny'])
def test_modify_not_reset(q):assert not new_build(q)


def test_new_custom_cannot_receive_old_deck(stores):
    install(stores,[pokemon('new-gengar','Mega Gengar ex')])
    svc,calls=service(stores,[custom,custom]);first=ask(svc,'Make me a Pikachu deck')
    r=ask(svc,'I like Gengar, build me something',first['conversation_id'])
    e=calls[1]
    assert e['history']==[] and e['artifacts']=={} and e['previous_proposal'] is None
    assert 'current_generated_deck' not in e and 'pending_changes' not in e
    assert 'Gengar' in e['selected_core']['canonical_name']
    assert r['answer']['proposal']['total_cards']==60
    assert all('Pikachu' not in c['canonical_name'] for c in r['answer']['proposal']['cards'])
    assert 'Gengar' in state(svc,r)['selected_core']['canonical_name']


def test_modify_preserves_artifact_source(novel):
    svc,calls=service(novel,[custom,change]);first=ask(svc,'Build me Mega Lopunny ex')
    before=deepcopy(state(svc,first)['generated_deck'])
    r=ask(svc,'Add Gengar to this deck',first['conversation_id'])
    assert calls[1]['current_generated_deck']['id']==before['id']
    assert calls[1]['generated_intent']=='RECOMMEND' and not calls[1]['new_build']
    assert state(svc,r)['generated_deck']==before


def test_one_compact_contract_recovery(novel):
    def repaired(e):
        value=obj(e);value.pop('rationale',None)
        return json.dumps(value)
    svc,calls=service(novel,['Concept. <POKELAB_ACTIONS>{broken',repaired])
    r=ask(svc,'Build me a 60-card Mega Lopunny ex deck')
    assert len(calls)==2 and calls[1]['version']=='pokelab-custom-contract-repair-v1'
    assert 'history' not in calls[1] and 'broken' not in json.dumps(calls[1])
    assert calls[1]['selected_core']['candidate_id']==calls[0]['selected_core']['candidate_id']
    assert r['answer']['proposal']['total_cards']==60 and r['answer']['proposal']['validation_status']=='VALIDATED'
    assert r['execution']['contract_repair_calls']==1 and 'build_failure' not in r['answer']


@pytest.mark.parametrize('repair',['not json',httpx.Response(429,json={'error':{'code':429}})])
def test_failed_repair_preserves_previous_artifact(novel,repair):
    svc,calls=service(novel,[custom,'<POKELAB_ACTIONS>{broken',repair]);first=ask(svc,'Build me Mega Lopunny ex')
    previous=deepcopy(state(svc,first)['generated_deck'])
    r=ask(svc,'Build me a new Mega Lopunny ex deck',first['conversation_id'])
    assert len(calls)==3 and r['answer']['build_failure']['reason'] in ('contract_repair_invalid','contract_repair_provider_failure')
    assert 'proposal' not in r['answer'] and state(svc,r)['generated_deck']==previous


@pytest.mark.parametrize('theme,energy',[('Pikachu',32),('Gengar',20)])
def test_energy_padding_normalized(novel,theme,energy):
    stores=novel
    if theme=='Gengar':install(stores,[pokemon('g-shape','Mega Gengar ex')])
    svc,calls=service(stores,[lambda e:actions(obj(e,energy=energy))]);r=ask(svc,f'Make me a {theme} deck')
    assert 'proposal' in r['answer'],r['answer'].get('build_failure')
    report=r['answer']['proposal']
    assert report['total_cards']==60 and report['validation_status']=='VALIDATED'
    assert report['category_subtotals']['Energy']<=14 and report['category_subtotals']['Trainer']>=28
    assert report['shape_debug']['mode']=='custom_shape_normalization' and len(calls)==1
    assert calls[0]['custom_shape_prior']['soft'] and 'custom Standard build' in r['answer']['paragraphs'][0]['text']


def test_overfilled_cuts_energy_first(novel):
    svc,calls=service(novel,[lambda e:actions(obj(e,62))]);r=ask(svc,'Build me Mega Lopunny ex')
    report=r['answer']['proposal']
    assert report['total_cards']==60 and report['validation_status']=='VALIDATED' and len(calls)==1
    assert all(k.startswith('deck-basic-energy:') for k in report['shape_debug']['removed'])
    assert next(c for c in report['cards'] if c['canonical_name']=='Mega Lopunny ex')['quantity']==4


def test_high_energy_mechanical_exception(stores):
    card=pokemon('energy-core','Gengar ex')
    card['attacks'][0]['effect']='This attack does 20 damage for each Energy attached to this Pokémon.'
    install(stores,[card]);svc,calls=service(stores,[lambda e:actions(obj(e,energy=30))]);r=ask(svc,'Build me a Gengar ex deck')
    assert r['answer']['proposal']['category_subtotals']['Energy']==30
    assert r['answer']['proposal']['shape_debug']['energy_exception_reasons']==['printed_core_energy_scaling']
    assert r['answer']['proposal']['validation_status']=='VALIDATED'


def test_sufficient_energy_fill_prefers_support(novel):
    from test_agent_default_forward import delta
    svc,calls=service(novel,[lambda e:actions(obj(e,56,energy=10)),'bad delta'])
    r=ask(svc,'Build me Mega Lopunny ex')
    assert r['answer']['proposal']['total_cards']==60
    assert r['answer']['proposal']['category_subtotals']['Energy']==10
