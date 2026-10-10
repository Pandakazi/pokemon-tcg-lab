"""Three build sources, novice themes, and budget/state boundaries; fake transport only."""
from copy import deepcopy
import json
import sqlite3
import pytest
from pokelab.agent_research import ResearchRequest
from test_agent_consensus import cohort,quality,stores,sources,setup,research,offline
from test_agent_deck_completion import service
from test_agent_resolution_reprints import install


def ask(svc,q,key=None):
    return svc.run(ResearchRequest(scope='conversation',question=q,conversation_id=key))


def actions(value):return '<POKELAB_ACTIONS>'+json.dumps(value)+'</POKELAB_ACTIONS>'


@pytest.fixture
def novel(quality):
    stores,_=quality
    install(stores,[dict(id='lopunny',name='Mega Lopunny ex',category='Pokemon',stage='Basic',
        types=['Fighting'],attacks=[dict(name='Kick',cost=['Fire','Psychic'],damage=100)],
        regulationMark='H',legal={'standard':True},variants={'normal':True})])
    return stores


def custom(e):
    candidates=e['candidate_sandbox']['candidates']
    core=next(r for r in candidates if r['requested_core'] and r['category']=='Pokemon')
    trainers=[r for r in candidates if r['category']=='Trainer' and not r['ace_spec']][:10]
    energy=next(r for r in candidates if r['basic_energy'])
    selected={core['candidate_id']}
    pending=[core]
    while pending:
        for key in pending.pop().get('predecessor_candidate_ids',[]):
            if key not in selected:
                selected.add(key);pending.append(next(r for r in candidates if r['candidate_id']==key))
    rows=[*[dict(candidate_id=key,quantity=4) for key in sorted(selected)],*[dict(candidate_id=r['candidate_id'],quantity=4) for r in trainers]]
    rows.append(dict(candidate_id=energy['candidate_id'],quantity=60-sum(r['quantity'] for r in rows)))
    return 'I would test this custom setup. '+actions(dict(type='generated_deck',cards=rows,rationale='Custom legal core and support.'))


@pytest.mark.parametrize('q',[
    'Build me a 60-card Mega Lopunny ex deck.',
    "build me a 60 card mega lopunny EX. If you can't, recommend a deck that uses that card",
    'Can you make a deck with Lopunny?'])
def test_custom_pm_requests(novel,q):
    svc,calls=service(novel,[custom]);before={k:p.read_bytes() for k,p in novel.paths.items()}
    result=ask(svc,q);report=result['answer']['proposal']
    assert result['status']=='answered' and len(calls)==1
    assert report['build_mode']=='custom' and report['generation_source']=='custom_model_build'
    assert report['consensus_status']=='no_matching_variant'
    assert report['total_cards']==60 and report['validation_status']=='VALIDATED' and not report['unresolved']
    assert next(r for r in report['cards'] if r['canonical_name']=='Mega Lopunny ex')['quantity']==4
    assert 'custom Standard build' in result['answer']['paragraphs'][0]['text']
    assert before=={k:p.read_bytes() for k,p in novel.paths.items()}
    assert ask(svc,'Recount that deck.',result['conversation_id'])['answer']['proposal']['total_cards']==60
    assert len(calls)==1


@pytest.mark.parametrize('q',['Make me a Pikachu deck','I like Gengar, build me something'])
def test_novice_theme(stores,q):
    if 'Gengar' in q:
        install(stores,[dict(id='gengar',name='Gengar ex',category='Pokemon',stage='Basic',types=['Lightning'],
            attacks=[dict(name='Test',cost=['Lightning'],damage=40)],regulationMark='H',legal={'standard':True},variants={'normal':True})])
    svc,calls=service(stores,[custom]);result=ask(svc,q)
    assert result['answer']['proposal']['generation_source']=='custom_model_build'
    assert result['answer']['proposal']['validation_status']=='VALIDATED' and len(calls)==1


def test_novice_ambiguity_asks_once(novel):
    install(novel,[dict(id='lopunny-other',name='Mega Lopunny ex',category='Pokemon',stage='Basic',types=['Fire'],
        attacks=[dict(name='Other',cost=['Fire'],damage=100)],regulationMark='H',legal={'standard':True},variants={'normal':True})])
    svc,calls=service(novel,[custom]);r=ask(svc,'Can you make a deck with Lopunny?')
    assert not calls and 'proposal' not in r['answer']
    assert r['envelope']['generation']['failure_reason']=='ambiguous_legal_core'
    assert r['answer']['paragraphs'][0]['text'].count('?')==1
    precise=ask(svc,'Mega Lopunny ex — Kick',r['conversation_id'])
    assert precise['envelope']['generation']['generation_source']=='custom_model_build'
    assert precise['answer']['proposal']['validation_status']=='VALIDATED'
    assert len(calls)==1


@pytest.mark.parametrize('q',['Build me an Imaginarymon deck','Make me an Oldmon deck'])
def test_unknown_or_illegal_core_no_custom(stores,q):
    install(stores,[dict(id='oldmon',name='Oldmon',category='Pokemon',stage='Basic',types=['Fire'],
        attacks=[],regulationMark='G',legal={'standard':False},variants={'normal':True})])
    svc,calls=service(stores,['must not run']);r=ask(svc,q)
    assert not calls and 'proposal' not in r['answer']
    assert r['envelope']['generation']['generation_source'] is None


def explicit(cohort):
    with sqlite3.connect(cohort.paths['competitive']) as db:
        raw=dict(archetype_id='lopunny-dusknoir',archetype_name='Lopunny Dusknoir',cards=[],player='Fixture')
        db.execute('UPDATE competitive_decks SET raw=?',(json.dumps(raw),))
        # Existing source base label allows the unchanged selector to recognize an explicit variant.
        base=dict(raw,archetype_id='lopunny',archetype_name='Lopunny')
        row=db.execute('SELECT * FROM competitive_decks LIMIT 1').fetchone()
        db.execute('INSERT INTO competitive_decks VALUES (?,?,?,?,?,?)',(row[0],row[1],20,1,json.dumps(base),row[-1]))


@pytest.mark.parametrize('limit,bytes_limit',[(3,14000),(48,120)])
def test_explicit_consensus_bypasses_candidate_admission(cohort,monkeypatch,limit,bytes_limit):
    import pokelab.agent_deck_sandbox as sandbox
    explicit(cohort);monkeypatch.setattr(sandbox,'MAX_CANDIDATES',limit);monkeypatch.setattr(sandbox,'MAX_BYTES',bytes_limit)
    svc,calls=service(cohort,['must not run']);r=ask(svc,'build me a Lopunny Dusknoir deck')
    assert r['status']=='answered',r
    c=r['envelope']['candidate_sandbox']['consensus'];report=r['answer']['proposal']
    assert report['generation_source']=='recent_consensus_explicit_variant' and report['total_cards']==60
    assert report['validation_status']=='VALIDATED' and not calls
    assert {r['candidate_id']:r['quantity'] for r in report['cards']}=={r['candidate_id']:r['quantity'] for r in c['cards']}
    assert len(r['envelope']['candidate_sandbox']['candidates'])<len(c['cards'])
    assert len(r['envelope']['candidate_sandbox']['candidates'])<=limit
    assert ask(svc,'Recount that deck.',r['conversation_id'])['answer']['proposal']['total_cards']==60


def change(e):
    current=e['current_generated_deck']['cards'];energy=next(r for r in current if r['candidate_id'].startswith('deck-basic-energy:'))
    target=next(r for r in e['candidate_sandbox']['candidates'] if r['category']=='Trainer' and all(x['candidate_id']!=r['candidate_id'] for x in current))
    return 'I would test this support option. '+actions(dict(type='proposed_deck_changes',changes=[
        dict(action='remove',candidate_id=energy['candidate_id'],quantity=1),
        dict(action='add',candidate_id=target['candidate_id'],quantity=1)],rationale='Test support.'))


@pytest.mark.parametrize('question',['Critique this deck.','Why did you build it this way?','Was this a consensus deck?',"Why didn’t you use Limitless?"])
def test_custom_discussion_immutable(novel,question):
    malicious=actions(dict(type='generated_deck',cards=[dict(card_name='Invented',quantity=60)]))
    svc,calls=service(novel,[custom,'I would test its setup. '+malicious])
    first=ask(svc,'Build me Mega Lopunny ex');key=first['conversation_id'];before=deepcopy(svc.conversations.get(key)['artifacts'])
    r=ask(svc,question,key)
    assert r['status']=='answered' and svc.conversations.get(key)['artifacts']==before
    assert r['envelope']['current_generated_deck']['generation_source']=='custom_model_build'
    assert len(calls)==2


def test_custom_exact_changes_apply_recount(novel):
    svc,calls=service(novel,[custom,change]);first=ask(svc,'Build me Mega Lopunny ex');key=first['conversation_id']
    proposal=ask(svc,'What exact changes would you make?',key)
    assert svc.conversations.get(key)['artifacts']['proposed_change_set']['status']=='PROPOSED',proposal
    applied=ask(svc,'Make those changes.',key);report=applied['answer']['proposal']
    assert report['total_cards']==60 and report['generation_source']=='custom_model_build'
    assert len(calls)==2 and ask(svc,'Recount that deck.',key)['answer']['artifact_id']==applied['answer']['artifact_id']


def test_custom_cannot_omit_core(novel):
    def omit(e):
        energy=next(r for r in e['candidate_sandbox']['candidates'] if r['basic_energy'])
        return actions(dict(type='generated_deck',cards=[dict(candidate_id=energy['candidate_id'],quantity=60)]))
    svc,calls=service(novel,[omit]);r=ask(svc,'Build me Mega Lopunny ex')
    assert r['answer']['proposal']['validation_status']!='VALIDATED'
    assert r['answer']['completion']['status']=='incomplete'
    assert 'requested legal core' in ' '.join(r['answer']['proposal']['hard_validation'])


def test_insufficient_sample_custom_fallback(cohort):
    with sqlite3.connect(cohort.paths['competitive']) as db:db.execute('DELETE FROM competitive_decks WHERE rank>2')
    svc,calls=service(cohort,[custom]);r=ask(svc,'Build me a Dragapult deck')
    assert r['envelope']['generation']['build_mode']=='custom' and len(calls)==1
    assert r['envelope']['generation']['fallback_reason']=='insufficient_sample'


def test_explicit_consensus_without_generic_label(cohort):
    explicit(cohort)
    with sqlite3.connect(cohort.paths['competitive']) as db:db.execute('DELETE FROM competitive_decks WHERE rank=20')
    svc,calls=service(cohort,['must not run']);r=ask(svc,'Build me Lopunny Dusknoir')
    assert r['answer']['proposal']['generation_source']=='recent_consensus_explicit_variant' and not calls


def test_direct_consensus_needs_no_provider_context_budget(cohort,monkeypatch):
    import pokelab.agent_conversation as conversation
    monkeypatch.setattr(conversation,'CONTEXT_BYTES',1)
    svc,calls=service(cohort,['must not run']);r=ask(svc,'Make me a Dragapult deck')
    assert r['answer']['proposal']['total_cards']==60 and not calls


def test_oversized_consensus_modification_keeps_bounded_new_candidates(cohort,monkeypatch):
    import pokelab.agent_deck_sandbox as sandbox
    monkeypatch.setattr(sandbox,'MAX_CANDIDATES',3)
    def reply(e):
        assert len(e['candidate_sandbox']['candidates'])<=3
        energies=[r for r in e['candidate_sandbox']['candidates'] if r['basic_energy']]
        return 'I would test this Energy balance. '+actions(dict(type='proposed_deck_changes',changes=[
            dict(action='remove',candidate_id=energies[0]['candidate_id'],quantity=1),
            dict(action='add',candidate_id=energies[1]['candidate_id'],quantity=1)],rationale='Test balance.'))
    svc,calls=service(cohort,[reply]);r=ask(svc,'Build me a Dragapult deck');key=r['conversation_id']
    assert len(r['answer']['proposal']['cards'])>3
    changed=ask(svc,'What exact changes would you make?',key)
    assert svc.conversations.get(key)['artifacts']['proposed_change_set']['status']=='PROPOSED',changed
    applied=ask(svc,'Make those changes.',key)
    assert applied['answer']['proposal']['total_cards']==60 and applied['answer']['proposal']['validation_status']=='VALIDATED'
    assert len(calls)==1


def test_custom_repair_retains_source_and_core(novel):
    def short(e):
        value=json.loads(custom(e).split('<POKELAB_ACTIONS>')[1].split('</POKELAB_ACTIONS>')[0])
        value['cards'][-1]['quantity']-=2
        return actions(value)
    def fill(e):
        energy=next(r for r in e['candidate_sandbox']['candidates'] if r['basic_energy'])
        return actions(dict(type='generated_deck_completion',adds=[dict(candidate_id=energy['candidate_id'],quantity=2)],removes=[]))
    svc,calls=service(novel,[short,fill]);r=ask(svc,'Build me Mega Lopunny ex')
    report=r['answer']['proposal']
    assert len(calls)==2 and report['total_cards']==60 and report['validation_status']=='VALIDATED'
    assert report['generation_source']=='custom_model_build' and report['requested_core_ids']
    assert 'custom Standard build' in r['answer']['paragraphs'][0]['text']


def test_custom_provenance_cannot_be_invented(novel):
    svc,calls=service(novel,[lambda e:'This is the recent competitive consensus. '+custom(e),
        'This is the current tournament shell. I would test its setup.'])
    r=ask(svc,'Build me Mega Lopunny ex');key=r['conversation_id']
    assert 'custom_provenance_claim_withheld' in r['answer']['notices']
    follow=ask(svc,'Critique this deck.',key)
    assert 'current tournament shell' not in ' '.join(x['text'] for x in follow['answer']['paragraphs'])
    assert 'custom_provenance_claim_withheld' in follow['answer']['notices']
