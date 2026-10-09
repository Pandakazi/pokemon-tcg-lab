import json
import pytest
from pokelab.agent_card_facts import reconcile
from pokelab import agent_conversation as c,agent_research as a
from test_agent_deck_proposals import stores,active,service
from test_card_pool_research import sources,setup,research,offline


@pytest.mark.parametrize('draft,expected,absent',[
 ('Pikachu ex uses Wrong Storm to heal everything. I would preserve the core.','Spark','Wrong Storm'),
 ('Pikachu ex uses Spark to heal everything. I would preserve the core.','Printed damage: 20','heal everything'),
 ('Munkidori gives free retreat through Wrong Ability. I would test this support role.','Adrena-Brain','Wrong Ability'),
 ('Recovery Tool recovers every Trainer. I would preserve recovery.','Put 2 Pokémon','every Trainer'),
 ('Alakazam uses a mysterious attack. The matchup needs testing.','multiple materially different','mysterious attack'),
 ('Recovery Tool blocks Phantom Ability so the matchup could be easier.','reviewed ruling','blocks Phantom'),
])
def test_named_facts_correct_without_losing_strategy(stores,draft,expected,absent):
    active(stores,[('qa-munkidori',1),('qa-energy',59)])
    svc,calls=service(stores,text=draft)
    result=svc.run(a.ResearchRequest(scope='conversation',question='Explain this plan.',include_deck=True,revision=7))
    assert result['status']=='answered'
    text=' '.join(p['text'] for p in result['answer']['paragraphs'])
    assert expected in text and absent not in text
    assert any(word in text for word in ('preserve','test','matchup'))
    assert len(calls)==1


def test_active_printing_wins_ambiguity_and_readonly(stores):
    active(stores,[('qa-alakazam2',1),('qa-energy',59)])
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    svc,_=service(stores,text='Alakazam has an Ability called First that draws cards. I would test this plan.')
    result=svc.run(a.ResearchRequest(scope='conversation',question='How does this deck work?',include_deck=True,revision=7))
    text=' '.join(p['text'] for p in result['answer']['paragraphs'])
    assert 'Second' in text and 'Heal 20 damage' in text and 'called First' not in text
    assert before=={k:p.read_bytes() for k,p in stores.paths.items()}


@pytest.mark.parametrize('text',['Raging Bolt is your main attacker.','This deck may sacrifice consistency for flexibility.'])
def test_casual_strategy_does_not_open_resolution(text):
    class Forbidden:
        def snapshot(self):raise AssertionError('No factual trigger')
    assert reconcile(text,Forbidden(),None,{})==(text,[])


def test_missing_fact_keeps_reasoning(stores):
    request=a.ResearchRequest(scope='conversation',question='Explain.')
    envelope=c.context(request,stores,dict(turns=[],printings=[]))
    text,facts=reconcile('Unknownmon uses Fake Storm so a slower plan could work. Keep experimenting.',stores,request,envelope)
    assert 'unresolved' in text and 'Keep experimenting' in text and 'Fake Storm' not in text


def test_hybrid_attack_correction_survives_quantity_filter(stores):
    import httpx
    from pokelab.agent_providers import Selection
    active(stores,[('qa-pikachu',4),('qa-energy',56)])
    def handle(req):
        assert 'response_format' not in json.loads(req.content)
        return httpx.Response(200,json={'choices':[{'message':{'content':'Pikachu ex uses Wrong Storm to do 999 damage. I would keep the core. <POKELAB_ACTIONS>{"changes":[{"action":"remove","card_name":"Lightning Energy","quantity":1},{"action":"add","card_name":"Draw Helper","quantity":1}]}</POKELAB_ACTIONS>'},'finish_reason':'stop'}]})
    svc=a.ResearchService(stores.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle))
    result=svc.run(a.ResearchRequest(scope='conversation',question='Give me exact cards and quantities.',include_deck=True,revision=7))
    text=' '.join(p['text'] for p in result['answer']['paragraphs'])
    assert result['status']=='answered' and 'Spark' in text and 'Printed damage: 20' in text
    assert 'Wrong Storm' not in text and '999' not in text and 'keep the core' in text
    assert result['answer']['proposal']['validation_status']=='VALIDATED'


@pytest.mark.parametrize('draft,expected',[
 ('Pikachu ex takes massive knockouts through its signature Wrong Storm attack. I would preserve the core.','Spark'),
 ('Adding a third Recovery Tool recovers every Trainer. I would test recovery.','Put 2 Pokémon'),
])
def test_embedded_fact_replacement_is_a_whole_sentence(stores,draft,expected):
    request=a.ResearchRequest(scope='conversation',question='Explain.')
    envelope=c.context(request,stores,dict(turns=[],printings=[]))
    text,_=reconcile(draft,stores,request,envelope)
    assert expected in text and 'Wrong Storm' not in text and 'every Trainer' not in text
    assert 'signature For' not in text and 'Adding a third' not in text
    assert 'resolved printing states' not in text and 'For Recovery Tool' not in text
    assert 'I would' in text


def test_unresolved_attack_removes_attached_precision(stores):
    request=a.ResearchRequest(scope='conversation',question='Explain.')
    envelope=c.context(request,stores,dict(turns=[],printings=[]))
    draft='The plan depends on Unknownmon uses Fake Storm. It deals 70 damage per Energy. You must discard 3 Energy. Strategically, pressure still matters.'
    text,_=reconcile(draft,stores,request,envelope)
    assert 'unresolved' in text and '70' not in text and '3 Energy' not in text
    assert 'Strategically, pressure still matters.' in text
    assert not text.startswith('The plan depends on I cannot')



def test_printed_effect_newlines_do_not_create_orphans(stores):
    from tcg_lab.card_db import SQLiteCards
    db=SQLiteCards(stores.paths['cards'])
    with stores.snapshot() as (dbs,errors):raw=json.loads(dbs['cards'].execute("SELECT raw FROM cards WHERE id='qa-recover'").fetchone()[0])
    raw['effect']='Search your deck for a Pokémon.\n\nThen, shuffle your deck..'
    db.put(raw)
    svc,_=service(stores,text='Recovery Tool recovers every Trainer. I would keep recovery.')
    result=svc.run(a.ResearchRequest(scope='conversation',question='Explain.'))
    paragraphs=[p['text'] for p in result['answer']['paragraphs']]
    assert not any(p.startswith('Then, shuffle') for p in paragraphs)
    assert not any('..' in p for p in paragraphs)
    assert any('Recovery Tool:' in p for p in paragraphs)
    assert any('Then, shuffle' in e['value'].get('effect','') for e in result['envelope']['evidence'])
