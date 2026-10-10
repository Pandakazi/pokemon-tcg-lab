"""Novice gameplay choices and real custom artifact boundaries; no live transport."""
from copy import deepcopy
import httpx
import pytest
from pokelab.agent_deck_sandbox import legal_pool
from test_agent_build_routing import novel,custom,ask,install,service,cohort,quality,stores,sources,setup,research,offline


def pokemon(key,name,damage=100,hp=250,attack='Test'):
    return dict(id=key,name=name,category='Pokemon',stage='Basic',hp=hp,types=['Lightning'],
        attacks=[dict(name=attack,cost=['Lightning'],damage=damage)],regulationMark='H',
        legal={'standard':True},variants={'normal':True})


def state(svc,result):return svc.conversations.get(result['conversation_id'])['artifacts']


def text(result):return ' '.join(p['text'] for p in result['answer']['paragraphs'])


def test_pikachu_printings_collapse_and_baby_does_not_win(stores):
    card=pokemon('pika-new','Pikachu ex',220)
    install(stores,[card,dict(card,id='pika-reprint'),pokemon('pika-baby','Pikachu',10,60)])
    pool=legal_pool(stores.paths['cards'])
    assert sum(r['card']['name']=='Pikachu ex' and r['card']['attacks'][0]['damage']==220 for r in pool)==1
    svc,calls=service(stores,[custom]);r=ask(svc,'Make me a Pikachu deck.')
    core=state(svc,r)['selected_core']
    assert core['canonical_name']=='Pikachu ex' and core['selection_source']=='auto_buildaround'
    assert core['format']=='standard' and core['status']=='RESOLVED' and core['source_turn']==1
    assert r['answer']['proposal']['total_cards']==60 and len(calls)==1
    assert 'Build-around: Pikachu ex.' in text(r)
    assert all(k not in text(r) for k in ('pika-new','pika-reprint','pika-baby'))


def test_gengar_auto_default_and_explicit_regular(stores):
    install(stores,[pokemon('g-mega','Mega Gengar ex'),pokemon('g-ex','Gengar ex',20),pokemon('g-baby','Gengar',10,60)])
    svc,calls=service(stores,[custom]);r=ask(svc,'I like Gengar, build me something.')
    assert state(svc,r)['selected_core']['canonical_name']=='Mega Gengar ex'
    assert r['answer']['proposal']['validation_status']=='VALIDATED' and len(calls)==1
    regular=ask(svc,'Build me a regular Gengar deck.')
    assert state(svc,regular)['selected_core']['canonical_name']=='Gengar'
    assert state(svc,regular)['selected_core']['selection_source']=='user_selected'


def test_true_gameplay_choice_persists_then_pronoun_builds(stores):
    install(stores,[pokemon('g-mega','Mega Gengar ex'),pokemon('g-ex','Gengar ex',300)])
    svc,calls=service(stores,['I would test the setup.',custom])
    first=ask(svc,'I like Gengar, build me something.')
    assert not calls and text(first) in ('Do you want Mega Gengar ex or Gengar ex?','Do you want Gengar ex or Mega Gengar ex?')
    chosen=ask(svc,'Mega Gengar EX.',first['conversation_id'])
    selected=deepcopy(state(svc,chosen)['selected_core'])
    assert selected['canonical_name']=='Mega Gengar ex' and selected['selection_source']=='user_selected'
    assert chosen['answer']['build_failure']['reason']=='structured_deck_not_returned'
    assert 'missing_artifact' not in chosen['answer']['notices']
    final=ask(svc,'build me a deck around it',first['conversation_id'])
    assert state(svc,final)['selected_core']==selected
    assert final['answer']['proposal']['total_cards']==60 and final['answer']['proposal']['build_mode']=='custom'
    assert len(calls)==2 and calls[-1]['selected_core']['candidate_id']==selected['candidate_id']


@pytest.mark.parametrize('q',['build me a deck around it','use that one','make a deck with that','build around that card'])
def test_selected_core_referents(novel,q):
    svc,calls=service(novel,[custom]);first=ask(svc,'Build me Mega Lopunny ex')
    core=deepcopy(state(svc,first)['selected_core'])
    again=ask(svc,q,first['conversation_id'])
    assert state(svc,again)['selected_core']==core
    assert again['answer']['proposal']['validation_status']=='VALIDATED' and len(calls)==2


def test_same_name_different_effects_only_gameplay_labels(stores):
    install(stores,[pokemon('p-a','Pikachu ex',300,250,'Voltage'),pokemon('p-b','Pikachu ex',300,250,'Thunder')])
    svc,calls=service(stores,[custom]);r=ask(svc,'Make me a Pikachu deck')
    assert not calls and 'Voltage' in text(r) and 'Thunder' in text(r)
    assert 'p-a' not in text(r) and 'p-b' not in text(r)
    choices=state(svc,r)['build_clarification']['choices']
    assert len({c['candidate_id'] for c in choices})==2
    final=ask(svc,'Pikachu ex — Voltage',r['conversation_id'])
    assert final['answer']['proposal']['validation_status']=='VALIDATED' and len(calls)==1


@pytest.mark.parametrize('reply,reason',[
    ('I would test the setup.','structured_deck_not_returned'),
    ('<POKELAB_ACTIONS>{broken}</POKELAB_ACTIONS>','generated_deck_contract_invalid'),
    (httpx.Response(429,json={'error':{'code':429}}),'provider_failure'),
    (httpx.Response(200,json={'choices':[{'message':{'content':'partial'},'finish_reason':'length'}]}),'output_token_limit_reached')])
def test_custom_failure_is_structured_and_remembers_core(novel,reply,reason):
    svc,calls=service(novel,[reply]);r=ask(svc,'Build me a 60-card Mega Lopunny ex deck.')
    assert r['answer']['build_failure']['reason']==reason and len(calls)==1
    assert r['answer']['completion']['status']=='incomplete'
    assert not r['answer']['notices'] and 'discussion' not in text(r)
    assert 'generated_deck' not in state(svc,r) and state(svc,r)['selected_core']['canonical_name']=='Mega Lopunny ex'


def test_candidate_coverage_failure_has_no_provider(novel,monkeypatch):
    import pokelab.agent_deck_sandbox as sandbox
    original=sandbox.legal_pool
    monkeypatch.setattr(sandbox,'legal_pool',lambda *a,**kw:[r for r in original(*a,**kw) if r['card']['name']=='Mega Lopunny ex'])
    svc,calls=service(novel,['must not call']);r=ask(svc,'Build me Mega Lopunny ex')
    assert not calls and r['answer']['build_failure']['reason']=='insufficient_legal_candidate_coverage'
    assert not r['answer']['notices']


def test_consensus_selected_core_and_state_immutable(cohort):
    svc,calls=service(cohort,['I would test its setup.']);r=ask(svc,'Make me a Dragapult deck')
    core=state(svc,r)['selected_core']
    assert core['selection_source']=='recent_consensus' and core['canonical_name']=='Dragapult ex'
    assert not calls and r['answer']['proposal']['total_cards']==60
    before=deepcopy(state(svc,r))
    recount=ask(svc,'Recount that deck.',r['conversation_id'])
    assert recount['answer']['proposal']['total_cards']==60 and state(svc,recount)==before and not calls
    critique=ask(svc,'Critique that deck.',r['conversation_id'])
    assert state(svc,critique)==before and len(calls)==1


def test_custom_budget_failure_preserves_selected_core(novel,monkeypatch):
    import pokelab.agent_conversation as conversation
    monkeypatch.setattr(conversation,'CONTEXT_BYTES',1)
    svc,calls=service(novel,['must not call']);r=ask(svc,'Build me Mega Lopunny ex')
    assert not calls and r['answer']['build_failure']['reason']=='required_context_overflow'
    assert state(svc,r)['selected_core']['canonical_name']=='Mega Lopunny ex'


def test_selected_core_cannot_be_replaced_by_generic_consensus(cohort):
    install(cohort,[pokemon('d-other','Mega Dragapult ex')])
    svc,calls=service(cohort,[custom]);r=ask(svc,'Build me Mega Dragapult ex')
    assert r['answer']['proposal']['build_mode']=='custom' and len(calls)==1
    assert state(svc,r)['selected_core']['canonical_name']=='Mega Dragapult ex'
    assert r['answer']['proposal']['total_cards']==60


def test_new_unknown_request_does_not_reuse_previous_core(novel):
    svc,calls=service(novel,[custom]);first=ask(svc,'Build me Mega Lopunny ex')
    r=ask(svc,'Make me an Imaginarymon deck.',first['conversation_id'])
    assert len(calls)==1 and 'proposal' not in r['answer'] and not r['envelope'].get('selected_core')


@pytest.mark.parametrize('q',['I want a Charizard deck.','Can you make me a Charizard deck?'])
def test_other_novice_phrasing(stores,q):
    install(stores,[pokemon('c-ex','Charizard ex'),pokemon('c-baby','Charizard',10,60)])
    svc,calls=service(stores,[custom]);r=ask(svc,q)
    assert state(svc,r)['selected_core']['canonical_name']=='Charizard ex'
    assert r['answer']['proposal']['total_cards']==60 and len(calls)==1


def test_same_attack_name_labels_still_distinguish_gameplay(stores):
    a=pokemon('p-a','Pikachu ex',300,250,'Thunder');b=dict(a,id='p-b',attacks=[dict(a['attacks'][0],effect='Draw 2 cards.')])
    install(stores,[a,b]);svc,calls=service(stores,[custom]);r=ask(svc,'Make me a Pikachu deck')
    choices=state(svc,r)['build_clarification']['choices']
    assert not calls and len({c['label'] for c in choices})==2
    assert 'Draw 2 cards' in text(r) and all(k not in text(r) for k in ('p-a','p-b'))


def test_selected_exact_printing_overrides_novice_default(stores):
    from pokelab.agent_research import ResearchRequest
    install(stores,[pokemon('p-baby','Pikachu',10,60)])
    baby=next(r for r in legal_pool(stores.paths['cards']) if r['card']['name']=='Pikachu')
    svc,calls=service(stores,[custom])
    r=svc.run(ResearchRequest(scope='conversation',question='Make me a deck with this exact Pikachu.',printing=baby['printing_id']))
    assert state(svc,r)['selected_core']['candidate_id']==baby['functional_id']
    assert state(svc,r)['selected_core']['selection_source']=='user_selected' and len(calls)==1


def test_missing_core_due_candidate_budget_is_explicit(novel,monkeypatch):
    import pokelab.agent_deck_sandbox as sandbox
    monkeypatch.setattr(sandbox,'MAX_CANDIDATES',0)
    svc,calls=service(novel,['must not call']);r=ask(svc,'Build me Mega Lopunny ex')
    assert not calls and r['answer']['build_failure']['reason']=='candidate_budget_insufficient'


def test_custom_provider_contract_requires_real_artifact(novel,monkeypatch):
    import pokelab.agent_providers as providers
    original=providers.complete;systems=[]
    def capture(selection,system,*args,**kw):
        systems.append(system)
        return original(selection,system,*args,**kw)
    monkeypatch.setattr(providers,'complete',capture)
    svc,calls=service(novel,[custom]);r=ask(svc,'Build me a 60-card Mega Lopunny ex deck')
    assert r['answer']['proposal']['total_cards']==60 and len(systems)==len(calls)==1
    assert 'Zero artifacts is NOT a successful answer' in systems[0] and 'candidate_id selections totaling 60' in systems[0]


def test_gameplay_choice_survives_bounded_completion(stores):
    import json
    install(stores,[pokemon('p-a','Pikachu ex',300,250,'Voltage'),pokemon('p-b','Pikachu ex',300,250,'Thunder')])
    def short(e):
        value=json.loads(custom(e).split('<POKELAB_ACTIONS>')[1].split('</POKELAB_ACTIONS>')[0])
        value['cards'][-1]['quantity']-=2
        return '<POKELAB_ACTIONS>'+json.dumps(value)+'</POKELAB_ACTIONS>'
    def fill(e):
        energy=next(r for r in e['candidate_sandbox']['candidates'] if r['basic_energy'])
        return '<POKELAB_ACTIONS>'+json.dumps(dict(type='generated_deck_completion',adds=[dict(candidate_id=energy['candidate_id'],quantity=2)],removes=[]))+'</POKELAB_ACTIONS>'
    svc,calls=service(stores,[short,fill]);first=ask(svc,'Make me a Pikachu deck')
    choice=next(r for r in state(svc,first)['build_clarification']['choices'] if r['label'].endswith('Voltage'))
    final=ask(svc,choice['label'],first['conversation_id'])
    assert final['answer']['proposal']['total_cards']==60 and len(calls)==2
    assert state(svc,final)['selected_core']['candidate_id']==choice['candidate_id']
    assert state(svc,final)['selected_core']['selection_source']=='user_selected'
    assert state(svc,final)['selected_core']['source_turn']==2
