"""PM-equivalent novice/state/completion boundaries, entirely offline."""
from copy import deepcopy
import json
import httpx
import pytest
from pokelab.agent_research import ResearchRequest
from pokelab.agent_deck_sandbox import legal_pool
from test_agent_novice_core import pokemon,state,text
from test_agent_build_routing import novel,custom,ask,install,service,quality,stores,cohort,sources,setup,research,offline


def ability(card,name='Resolute Heart'):
    return dict(card,abilities=[dict(name=name,type='Ability',effect='Prevent a Knock Out while this Pokémon has full HP.')])


def short(e,n=56):
    value=json.loads(custom(e).split('<POKELAB_ACTIONS>')[1].split('</POKELAB_ACTIONS>')[0])
    value['cards'][-1]['quantity']-=60-n
    return '<POKELAB_ACTIONS>'+json.dumps(value)+'</POKELAB_ACTIONS>'


def delta(e,n=None):
    trainer=next(r for r in e['candidate_sandbox']['candidates'] if r['category']=='Trainer' and not r['ace_spec'] and all(c['candidate_id']!=r['candidate_id'] for c in e['repair']['cards']))
    return '<POKELAB_ACTIONS>'+json.dumps(dict(type='generated_deck_completion',adds=[dict(candidate_id=trainer['candidate_id'],quantity=n or e['repair']['required_delta'])],removes=[]))+'</POKELAB_ACTIONS>'


def test_pikachu_practical_default(stores):
    install(stores,[ability(pokemon('heart','Pikachu ex',300,200,'Topaz Bolt')),pokemon('tail','Pikachu ex',220,190,'Thunder')])
    svc,calls=service(stores,[custom]);r=ask(svc,'Make me a Pikachu deck')
    assert len(calls)==1 and r['answer']['proposal']['total_cards']==60
    assert state(svc,r)['selected_core']['display_name']=='Pikachu ex with Resolute Heart'
    assert 'Resolute Heart' in text(r) and '?' not in text(r)


def test_catalog_formatting_equivalents_collapse_for_selection_only(stores):
    card=ability(pokemon('g-a','Mega Gengar ex',230,350,'Void Gale'),'Shadowy Concealment')
    card['weaknesses']=[dict(type='Fighting',value='×2')]
    install(stores,[card,dict(card,id='g-b',suffix='ex'),dict(card,id='g-c',suffix='ex',weaknesses=[dict(type='Fighting',value='x2')])])
    before=stores.paths['cards'].read_bytes();pool=legal_pool(stores.paths['cards'])
    assert sum(r['card']['name']=='Mega Gengar ex' for r in pool)==3
    svc,calls=service(stores,[custom]);r=ask(svc,'I like Gengar, build me something')
    assert len(calls)==1 and r['answer']['proposal']['total_cards']==60 and '?' not in text(r)
    assert stores.paths['cards'].read_bytes()==before


@pytest.mark.parametrize('reply',['resolute heart','Pikachu ex — Resolute Heart'])
def test_partial_ability_choice_resumes_pending_build(stores,reply):
    install(stores,[ability(pokemon('p-a','Pikachu ex',300,250,'Bolt')),ability(pokemon('p-b','Pikachu ex',300,250,'Thunder'),'Hustle')])
    svc,calls=service(stores,[custom]);first=ask(svc,'Make me a Pikachu deck')
    assert not calls and state(svc,first)['pending_build']['status']=='awaiting_core'
    r=ask(svc,reply,first['conversation_id'])
    assert len(calls)==1 and r['answer']['proposal']['total_cards']==60
    assert 'pending_build' not in state(svc,r) and state(svc,r)['selected_core']['selection_source']=='user_selected'
    assert 'Resolute Heart' in state(svc,r)['selected_core']['display_name']


@pytest.mark.parametrize('reply',['yes','Mega Gengar ex','build a deck around it'])
def test_new_gengar_pending_cannot_bind_to_previous_pikachu(stores,reply):
    install(stores,[pokemon('g-mega','Mega Gengar ex'),pokemon('g-ex','Gengar ex',300)])
    svc,calls=service(stores,[custom]);pika=ask(svc,'Make me a Pikachu deck')
    first=svc.run(ResearchRequest(scope='conversation',question='I like Gengar, build me something',conversation_id=pika['conversation_id'],printing='qa-pikachu'))
    pending=state(svc,first)['pending_build']
    assert 'selected_core' not in state(svc,first) and all('Gengar' in c['canonical_name'] for c in pending['choices'])
    r=ask(svc,reply,pika['conversation_id'])
    if reply in ('yes','build a deck around it'):
        assert len(calls)==1 and state(svc,r)['pending_build']['theme']=='gengar'
        assert 'proposal' not in r['answer'] and 'Pikachu' not in text(r)
        r=ask(svc,'Mega Gengar ex',pika['conversation_id'])
    assert len(calls)==2 and r['answer']['proposal']['total_cards']==60
    assert 'Gengar' in state(svc,r)['selected_core']['canonical_name']
    follow=ask(svc,'build a deck around it',pika['conversation_id'])
    assert 'Gengar' in state(svc,follow)['selected_core']['canonical_name'] and len(calls)==3


@pytest.mark.parametrize('n',[56,59])
@pytest.mark.parametrize('reply',[lambda e:delta(e),'no action block',lambda e:delta(e,1),httpx.Response(429,json={'error':{'code':429}})])
def test_underfilled_custom_finishes_exact_sixty(novel,n,reply):
    svc,calls=service(novel,[lambda e:short(e,n),reply]);before={k:p.read_bytes() for k,p in novel.paths.items()}
    r=ask(svc,'Build me a 60-card Mega Lopunny ex deck')
    report=r['answer']['proposal']
    assert len(calls)==2 and report['total_cards']==60 and report['validation_status']=='VALIDATED'
    assert calls[1]['repair']['required_delta']==60-n
    assert r['answer']['completion']['status']=='complete' and 'build_failure' not in r['answer']
    assert report['construction_violations']==[] and not report['unresolved']
    energy_before=sum(c['quantity'] for c in calls[1]['repair']['cards'] if c['candidate_id'].startswith('deck-basic-energy:'))
    assert report['category_subtotals']['Energy']==energy_before
    assert before=={k:p.read_bytes() for k,p in novel.paths.items()}
    assert ask(svc,'Recount that deck.',r['conversation_id'])['answer']['proposal']['total_cards']==60 and len(calls)==2
    if not callable(reply):assert report['completion_debug']['mode']=='deterministic_ranked_fill'


def test_safe_fill_failure_is_not_fake_success(novel,monkeypatch):
    import pokelab.agent_deck_completion as completion
    monkeypatch.setattr(completion,'final_fill',lambda r:(None,{'reason':'insufficient_safe_completion_candidates'}))
    svc,calls=service(novel,[short,'no delta']);r=ask(svc,'Build me Mega Lopunny ex')
    assert r['answer']['completion']['status']=='incomplete' and r['answer']['build_failure']['reason']=='insufficient_safe_completion_candidates'
    assert r['answer']['proposal']['total_cards']==56 and len(calls)==2


def test_comparison_fields_do_not_collapse_different_effects(stores):
    from pokelab.agent_build_core import collapse
    card=pokemon('g-a','Mega Gengar ex')
    install(stores,[card,dict(card,id='g-b',attacks=[dict(card['attacks'][0],effect='Draw 2 cards.')])])
    pool=[r for r in legal_pool(stores.paths['cards']) if r['card']['name']=='Mega Gengar ex']
    assert len(collapse(pool,{}))==2


def test_larger_valid_deficit_uses_bounded_local_completion(novel):
    svc,calls=service(novel,[lambda e:short(e,45)])
    r=ask(svc,'Build me Mega Lopunny ex')
    assert len(calls)==1 and r['answer']['proposal']['total_cards']==60
    assert r['answer']['proposal']['validation_status']=='VALIDATED'
    assert r['answer']['proposal']['completion_debug']['mode']=='deterministic_ranked_fill'
    assert 2<=r['answer']['proposal']['category_subtotals']['Energy']<=16


def test_safe_completion_does_not_introduce_orphan_evolution(novel,monkeypatch):
    import pokelab.agent_deck_sandbox as sandbox
    install(novel,[dict(pokemon('orphan','Orphan ex'),stage='Stage2')])
    original=sandbox.build
    def with_orphan(*args,**kw):
        value=original(*args,**kw)
        row=next(r for r in sandbox.legal_pool(novel.paths['cards']) if r['card']['name']=='Orphan ex')
        value['candidates'].append(dict(candidate_id=row['functional_id'],printing_id=row['printing_id'],name='Orphan ex',category='Pokemon',stage='Stage2',basic_energy=False,ace_spec=False,copy_limit_name='orphan ex',requested_core=False,ranking={'score':99999,'roles':['draw-consistency']}))
        return value
    monkeypatch.setattr(sandbox,'build',with_orphan)
    svc,calls=service(novel,[short,'bad delta']);r=ask(svc,'Build me Mega Lopunny ex')
    assert r['answer']['proposal']['total_cards']==60
    assert all(c['canonical_name']!='Orphan ex' for c in r['answer']['proposal']['cards'])


def test_internal_completion_error_is_bounded_system_failure(novel,monkeypatch):
    import pokelab.agent_deck_completion as completion
    def broken(report):raise RuntimeError('Unsafe arbitrary detail must stay private')
    monkeypatch.setattr(completion,'final_fill',broken)
    svc,calls=service(novel,[short,'bad delta']);r=ask(svc,'Build me Mega Lopunny ex')
    assert r['answer']['build_failure']['reason']=='internal_completion_assessment_failure'
    assert 'Unsafe arbitrary' not in json.dumps(r)
