"""Offline regressions for formatting-only resolution and non-regressing repair."""
import json
import sqlite3
import pytest
from tcg_lab.card_db import SQLiteCards
from pokelab.agent_deck_proposals import Resolver,Candidate
from pokelab.agent_context_sources import SnapshotCards,SnapshotCollection
from pokelab.engine import functional_signature
from pokelab import agent_research as a
from test_agent_finalize_repair import service,deck,FULL
from test_agent_deck_proposals import stores
from test_card_pool_research import sources,setup,research,offline


def install(stores,records):
    cards=SQLiteCards(stores.paths['cards'])
    for raw in records:cards.put(dict(rarity='Uncommon',set={'id':'qa'},localId='1' if raw['id']=='legal-a' else raw['id'],**raw))
    with sqlite3.connect(stores.paths['cards']) as db:
        db.executemany("UPDATE cards SET game='tcg' WHERE id=?",[(r['id'],) for r in records])


def ball(id,effect,legal=True):
    return dict(id=id,name='Ultra Ball',category='Trainer',trainerType='Item',effect=effect,legal={'standard':legal},variants={'normal':True})


TEXT='You can use this card only if you discard 2 other cards from your hand.\n\nSearch your deck for a Pokémon, reveal it, and put it into your hand. Then, shuffle your deck.'


@pytest.mark.parametrize('printing',[None,'missing-id','qa-pikachu','old-ball'])
def test_generated_resolution_normalizes_formatting_and_bad_printing(stores,printing):
    records=[ball('legal-a',TEXT),ball('legal-b',TEXT.replace('\n\n','\n')),ball('old-ball',TEXT.replace('\n\n','\t'),False)]
    install(stores,records)
    assert functional_signature(records[0])!=functional_signature(records[1]) # stored identities unchanged
    with stores.snapshot() as (dbs,_):
        r=Resolver(SnapshotCollection(SnapshotCards(stores.paths['cards'],dbs['cards']),stores.paths['collection'],dbs['collection']),stores.paths['cards'])
        result,state,_=r.resolve(Candidate(name='Ultra Ball',printing_id=printing),generated=True)
        assert state=='resolved' and result['card']['id']=='legal-a'
        if printing=='qa-pikachu':assert r.resolve(Candidate(name='Ultra Ball',printing_id=printing))[1]=='name_printing_mismatch'


def test_different_effects_remain_ambiguous_and_illegal_old_not_equated(stores):
    install(stores,[ball('legal-a',TEXT),ball('legal-b',TEXT.replace('2 other','3 other')),ball('old-ball','Search your deck for any card.',False)])
    with stores.snapshot() as (dbs,_):
        r=Resolver(SnapshotCollection(SnapshotCards(stores.paths['cards'],dbs['cards']),stores.paths['collection'],dbs['collection']),stores.paths['cards'])
        assert r.resolve(Candidate(name='Ultra Ball'),generated=True)[1]=='ambiguous'
        assert r.resolve(Candidate(name='Ultra Ball',printing_id='old-ball'),generated=True)[1]=='ambiguous'  # Old hint cannot choose between distinct legal identities.
        assert r.resolve(Candidate(name='Ultra Ball',printing_id='qa-pikachu'),generated=True)[1]=='ambiguous'


def test_generated_service_uses_legal_name_before_mechanical_replacements(stores):
    install(stores,[ball('legal-a',TEXT),ball('legal-b',TEXT.replace('\n\n','\n'))])
    svc,calls=service(stores,[deck([FULL[0],('Ultra Ball','qa-recover',4,'search'),FULL[2]])])
    result=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete legal 60-card Standard deck.'))
    report=result['answer']['proposal']
    assert report['validation_status']=='VALIDATED' and not report['alternatives'], json.dumps({'hard':report['hard_validation'],'unresolved':report['unresolved']})
    assert report['cards'][1]['printing_id']=='legal-a' and len(calls)==1


def test_call_bell_24_to_23_repair_cannot_replace_or_persist_worse_list(stores):
    install(stores,[dict(id='sv08-165',name='Call Bell',category='Trainer',trainerType='Item',legal={'standard':True},variants={'normal':True},effect='You can use this card only if you go second, and only during your first turn.\n\nSearch your deck for a Supporter card, reveal it, and put it into your hand. Then, shuffle your deck.')])
    base=[FULL[0],('Lightning Energy','qa-energy',19,'energy')]
    original=base+[('Call Bell','sv08-165',1,'supporter search')]
    svc,calls=service(stores,[deck(original),deck(base),deck(base)])
    first=svc.run(a.ResearchRequest(scope='conversation',question='Create a complete legal 60-card Standard deck.'))
    assert first['answer']['proposal']['total_cards']==60 and len(calls)==1
    assert first['answer']['completion']['status']=='complete'
    assert first['answer']['proposal']['completion_debug']['mode']=='deterministic_ranked_fill'
    assert any(c['printing_id']=='sv08-165' for c in first['answer']['proposal']['cards'])
    follow=svc.run(a.ResearchRequest(scope='conversation',question='Finish it.',conversation_id=first['conversation_id']))
    assert follow['answer']['proposal']['total_cards']==60 and len(calls)==1
    stored=svc.conversations.get(first['conversation_id'])['artifacts']['generated_deck']['report']
    assert stored['total_cards']==60 and any(c['printing_id']=='sv08-165' for c in stored['cards'])
    recount=svc.run(a.ResearchRequest(scope='conversation',question='Recount that deck.',conversation_id=first['conversation_id']))
    assert recount['answer']['proposal']['total_cards']==60 and len(calls)==1
