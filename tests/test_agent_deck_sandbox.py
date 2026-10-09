"""Legal-first fixtures; all provider execution uses MockTransport."""
import json
from copy import deepcopy
import pytest
from pokelab.agent_deck_sandbox import legal_pool,build,small_repair,repair_distance
from pokelab.agent_deck_proposals import evaluate,Proposal,Candidate
from pokelab.agent_conversation import context
from pokelab import agent_research as a
from test_agent_finalize_repair import service,deck,FULL
from test_agent_resolution_reprints import install,ball,TEXT
from test_agent_deck_proposals import stores
from test_card_pool_research import sources,setup,research,offline


def test_legal_pool_deduplicates_and_ignores_stale_flags(stores):
    old=ball('old',TEXT,False);old['regulationMark']='G'
    current=ball('legal-a',TEXT,False);current['regulationMark']='H'
    fancy=ball('fancy',TEXT,True);fancy['regulationMark']='H'
    illegal=ball('rotated','Draw 7 cards.');illegal['regulationMark']='G'
    install(stores,[old,current,fancy,illegal])
    rows=legal_pool(stores.paths['cards'])
    matches=[r for r in rows if r['card']['name']=='Ultra Ball']
    assert len(matches)==1 and matches[0]['printing_id']=='legal-a'
    assert 'qa-old' not in {r['printing_id'] for r in rows}
    packet=build(stores.paths['cards'],'Build a Standard deck with draw and search')
    assert all(c['candidate_id'] in {r['functional_id'] for r in rows} for c in packet['candidates'])
    assert not any(c['printing_id'] in ('old','rotated','qa-old') for c in packet['candidates'])


def test_dragapult_family_support_packet(stores):
    cards=[]
    for id,name,stage,parent in [('dreepy','Dreepy','Basic',None),('drakloak','Drakloak','Stage1','Dreepy'),('dragapult','Dragapult ex','Stage2','Drakloak')]:
        raw=dict(id=id,name=name,category='Pokemon',stage=stage,legal={'standard':True},regulationMark='H',variants={'normal':True},attacks=[dict(name='Attack',cost=['Psychic'],damage=30)])
        if parent:raw['evolveFrom']=parent
        cards.append(raw)
    install(stores,cards)
    packet=build(stores.paths['cards'],'Build a Standard Dragapult ex deck')
    names={r['name'] for r in packet['candidates']}
    assert {'Dreepy','Drakloak','Dragapult ex','Recovery Tool','Draw Helper'}<=names
    assert 'Old Recovery' not in names
    assert len(packet['candidates'])<=48
    assert any(c['role']=='requested-core' and c['name']=='Dragapult ex' for c in packet['candidates'])


def test_outside_even_legal_card_rejected(stores):
    request=a.ResearchRequest(scope='conversation',question='Build a Standard deck')
    env=context(request,stores,dict(turns=[],printings=[]))
    env['candidate_sandbox']['candidates']=[c for c in env['candidate_sandbox']['candidates'] if c['name']!='Pikachu ex']
    report,_,_=evaluate(Proposal(kind='list',cards=(Candidate(name='Pikachu ex',quantity=4),)),(),stores,request,env)
    assert report['total_cards']==0
    assert report['unresolved'][0]['state']=='outside_candidate_sandbox'


def test_small_59_repair_and_same_sandbox(stores):
    short=[FULL[0],FULL[1],('Lightning Energy','wrong-provider-id',51,'energy')]
    svc,calls=service(stores,[deck(short),deck(FULL)])
    result=svc.run(a.ResearchRequest(scope='conversation',question='Build a Standard deck'))
    assert result['answer']['proposal']['total_cards']==60
    assert result['answer']['proposal']['validation_status']=='VALIDATED'
    assert len(calls)==2
    envelopes=[json.loads(c['messages'][1]['content']) for c in calls]
    assert envelopes[0]['candidate_sandbox']==envelopes[1]['candidate_sandbox']
    assert envelopes[1]['repair']['total']==59


def test_mass_invalid_no_repair_and_recount_preserved(stores):
    svc,calls=service(stores,[deck([FULL[0],('Invented Card',None,56,'support')])])
    result=svc.run(a.ResearchRequest(scope='conversation',question='Build a Standard deck'))
    assert len(calls)==1 and result['answer']['proposal']['total_cards']==4
    assert result['answer']['completion']['reason']=='generation_failure_exceeds_small_repair'
    follow=svc.run(a.ResearchRequest(scope='conversation',question='Finish it.',conversation_id=result['conversation_id']))
    assert len(calls)==1 and follow['answer']['proposal']['total_cards']==4


def test_small_repair_cannot_redesign_valid_slots(stores):
    short=[FULL[0],FULL[1],('Lightning Energy',None,51,'energy')]
    changed=[FULL[0],FULL[1],('Lightning Energy',None,40,'energy'),('Darkness Energy',None,12,'energy')]
    svc,calls=service(stores,[deck(short),deck(changed)])
    result=svc.run(a.ResearchRequest(scope='conversation',question='Build a Standard deck'))
    assert len(calls)==2 and result['answer']['proposal']['total_cards']==59
    assert result['answer']['completion']['reason']=='repair_scope_exceeded'


def test_small_repair_cannot_regress(stores):
    short=[FULL[0],FULL[1],('Lightning Energy',None,51,'energy')]
    worse=[FULL[0],FULL[1],('Lightning Energy',None,50,'energy')]
    svc,calls=service(stores,[deck(short),deck(worse)])
    result=svc.run(a.ResearchRequest(scope='conversation',question='Build a Standard deck'))
    assert len(calls)==2 and result['answer']['proposal']['total_cards']==59
    assert result['answer']['completion']['reason']=='repair_regressed'


def test_name_copy_limit_spans_distinct_functional_cards(stores):
    install(stores,[ball('legal-a',TEXT),ball('legal-b',TEXT.replace('2 other','3 other'))])
    rows=[FULL[0],('Ultra Ball','legal-a',3,'search'),('Ultra Ball','legal-b',2,'search'),('Lightning Energy',None,51,'energy')]
    svc,calls=service(stores,[deck(rows)])
    result=svc.run(a.ResearchRequest(scope='conversation',question='Build a Standard deck'))
    report=result['answer']['proposal']
    assert report['total_cards']==60 and not report['unresolved']
    assert report['validation_status']=='NEEDS_REPAIR'
    assert any('4' in reason and 'ultra ball' in reason.lower() for reason in report['hard_validation'])


def test_build_never_calls_legacy_retrieval(stores,monkeypatch):
    from pokelab.alternative_retrieval import RetrievalIndex
    monkeypatch.setattr(RetrievalIndex,'from_database',classmethod(lambda *args:pytest.fail('legacy retrieval used')))
    svc,calls=service(stores,[deck([FULL[0],('Unknown',None,4,'recovery'),FULL[2]]),deck(FULL)])
    result=svc.run(a.ResearchRequest(scope='conversation',question='Build a Standard deck'))
    assert result['answer']['proposal']['validation_status']=='VALIDATED'
    assert len(calls)==2
