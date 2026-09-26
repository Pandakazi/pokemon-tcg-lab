"""No-provider context proof. Fixtures write only before read-only guards engage."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import socket
import sqlite3
import pytest
from pydantic import ValidationError

from pokelab.agent_context import build, canonical
from pokelab.agent_context_models import Request
from pokelab.agent_context_sources import Sources
from pokelab.agent_rules_view import rules_view
from pokelab.collection import identity
from pokelab.decks import deck_identity, blank
from pokelab.rules.models import digest
from pokelab.rules import apply, evaluate, Choices
from pokelab.rules.registry import reviewed_sources
from tcg_lab.card_db import SQLiteCards
from test_research import research, seed, KEY, TODAY
from test_rules_costs_choices import Cards, scenario, action, paid


@pytest.fixture
def setup(research):
    seed(research,[4]*16,unmapped=1)
    root=research.collection.path.parent
    cards=SQLiteCards(research.collection.cards.path)
    basic=cards.get('sm2-1')['card']; basic['variants']={'normal':True}; cards.put(basic)
    for key,raw in reviewed_sources().items():
        record=deepcopy(raw); record.update(set={'id':key.rsplit('-',1)[0]},localId=key.rsplit('-',1)[1],variants={'normal':True,'holo':True})
        cards.put(record)
    catalog=research.collection.catalog()[0]
    document=blank(); document.update(has_saved=True,dirty=False,name='Fixture')
    for printing,count in (('sm2-1',4),('sm2-3',56)):
        record=catalog[printing]
        document['entries'].append(dict(identity=deck_identity(record),quantity=count,name=record['card']['name'],
            category=record['card']['category'],allocations=[dict(printing_id=printing,variant='normal',quantity=count)]))
    workspace=root/'workspace.sqlite3'
    with sqlite3.connect(workspace) as db:
        db.executescript('CREATE TABLE workspace(id INTEGER PRIMARY KEY,revision INTEGER,document TEXT); CREATE TABLE saved_decks(id TEXT,document TEXT,updated_at TEXT); CREATE TABLE default_printings(identity TEXT,printing_id TEXT,variant TEXT); PRAGMA user_version=2;')
        db.execute('INSERT INTO workspace VALUES (1,7,?)',(json.dumps(document),))
    research.collection.update('sm2-1','normal',quantity=3)
    research.collection.update('sm2-1','unspecified',quantity=2)
    sources=Sources(cards=cards.path,collection=research.collection.path,workspace=workspace,competitive=research.competitive.path)
    return sources,research


def request(**updates):
    return Request(question='Compare this card with my deck and evidence.',printing='sm2-1',as_of=TODAY,**updates)


def payload(packet,kind): return next(e.payload for e in packet.evidence if e.payload.kind==kind)


def test_compact_deterministic_readonly_packet_and_service_parity(setup,monkeypatch):
    sources,research=setup
    expected=research.competitive.stats(research.collection.catalog()[0]['sm2-1']['functional_id'],'30',today=TODAY,include_trend=False)
    before={k:p.read_bytes() for k,p in sources.paths.items()}
    connect=sqlite3.connect
    def guarded(path,*args,**kwargs):
        assert kwargs.get('uri') and '?mode=ro' in str(path), 'Agent attempted writable DB connection'
        return connect(path,*args,**kwargs)
    monkeypatch.setattr(sqlite3,'connect',guarded)
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('Network forbidden'))
    packet=build(request(archetype=KEY),sources)
    assert packet==build(request(archetype=KEY),sources)
    assert packet.status=='ready',packet.coverage
    actual=payload(packet,'competitive')
    for key in ('status','sample_size','included_decks','usage_percent','excluded_unmapped','results_without_lists'):
        assert getattr(actual,key)==expected[key]
    assert actual.sample_size==16 and actual.excluded_unmapped==1
    assert actual.archetypes[0].prevalence_percent==100
    deck=payload(packet,'deck'); assert deck.total==60 and deck.selected_quantity==4 and deck.revision==7
    assert deck.validation_state=='VALID' and not deck.dirty
    owned=payload(packet,'ownership'); assert owned.functional_total==5
    assert {v.finish:v.quantity for v in owned.exact}=={'normal':3,'unspecified':2}
    assert packet.budget.serialized_bytes==len(canonical(packet).encode())<=24576
    assert packet.budget.estimated_tokens==(packet.budget.serialized_bytes+3)//4
    value=packet.model_dump(mode='json'); value.pop('content_hash'); assert packet.content_hash==digest(value)
    refs={r.id for r in packet.references}; assert all(set(e.references)<=refs for e in packet.evidence)
    assert len(refs)==len(packet.references)
    assert before=={k:p.read_bytes() for k,p in sources.paths.items()}
    assert all(e.classification!='UNKNOWN' for e in packet.evidence)
    with pytest.raises(ValidationError): packet.status='broken'
    with pytest.raises(ValidationError): deck.total=20


@pytest.mark.parametrize('missing',['cards','collection','workspace','competitive'])
def test_missing_store_never_created(setup,missing):
    sources,_=setup; sources.paths[missing]=sources.paths[missing].with_name('does-not-exist.sqlite3')
    packet=build(request(),sources)
    assert packet.status=='partial' and not sources.paths[missing].exists()
    assert any(missing in s for s in packet.coverage.unavailable)


@pytest.mark.parametrize('store,version',[('cards',0),('cards',9),('collection',0),('collection',9),('workspace',1),('workspace',9),('competitive',9)])
def test_incompatible_store_untouched(setup,store,version):
    sources,_=setup
    with sqlite3.connect(sources.paths[store]) as db: db.execute(f'PRAGMA user_version={version}')
    before=sources.paths[store].read_bytes(); packet=build(request(),sources)
    assert packet.status=='partial' and before==sources.paths[store].read_bytes()


def test_missing_card_format_unknown_and_profile_only(setup):
    sources,_=setup
    absent=request().model_copy(update={'printing':'missing-999'})
    assert build(absent,sources).status=='partial'
    packet=build(request(window='format'),sources)
    assert payload(packet,'competitive').status=='format_unavailable'
    assert payload(packet,'competitive').usage_percent is None
    req=request().model_copy(update={'printing':'me01-131'})
    rules=payload(build(req,sources),'rules')
    assert rules.review_support=='REVIEWED' and rules.status=='INSUFFICIENT_INFORMATION'
    assert rules.result_type=='profile-only' and not rules.execution_authorized
    assert rules.missing==('explicit-gameplay-scenario',)


def test_budget_drops_whole_evidence_and_large_card_fails_explicitly(setup):
    sources,_=setup
    packet=build(request(archetype=KEY),sources,cap_bytes=4096)
    assert packet.budget.serialized_bytes<=4096 and packet.coverage.omitted
    assert packet==build(request(archetype=KEY),sources,cap_bytes=4096)
    with sqlite3.connect(sources.paths['cards']) as db:
        raw=json.loads(db.execute("SELECT raw FROM cards WHERE id='sm2-1'").fetchone()[0]); raw['effect']='x'*40000
        db.execute("UPDATE cards SET raw=? WHERE id='sm2-1'",(json.dumps(raw),))
    packet=build(request(),sources)
    assert packet.status=='budget_exceeded' and packet.evidence==() and packet.budget.serialized_bytes<=24576


def test_corrupt_allocation_unavailable_without_repair(setup):
    sources,_=setup
    with sqlite3.connect(sources.paths['workspace']) as db:
        doc=json.loads(db.execute('SELECT document FROM workspace').fetchone()[0]); doc['entries'][0]['quantity']=3
        db.execute('UPDATE workspace SET document=?',(json.dumps(doc),))
    before=sources.paths['workspace'].read_bytes(); packet=build(request(),sources)
    assert not any(e.payload.kind=='deck' for e in packet.evidence)
    assert sources.paths['workspace'].read_bytes()==before


def test_basic_energy_key_and_composite_is_derived(setup):
    sources,_=setup
    req=request(archetype=KEY,include_composite=True).model_copy(update={'printing':'sm2-3'})
    packet=build(req,sources)
    assert payload(packet,'card').deck_identity.startswith('deck-basic-energy:')
    assert payload(packet,'deck').selected_quantity==56
    composite=next(e for e in packet.evidence if e.payload.kind=='composite')
    assert composite.classification=='DERIVED_FACT' and composite.payload.algorithm=='validated-observed-medoid-v1'
    assert all(e.classification=='EMPIRICAL_EVIDENCE' for e in packet.evidence if e.payload.kind=='observation')


@pytest.mark.parametrize('gum',[False,True])
def test_trusted_rules_privacy_and_authority(gum):
    cards=Cards(); s=scenario(); a=action(s,gum,Choices(exchange='pay1') if gum else paid()); result=evaluate(a,s,cards)
    printing='me01-110' if gum else 'me01-131'
    view,_=rules_view(cards,printing,(a,s,result,'alice'))
    assert view.status=='SUPPORTED_LEGAL' and not view.execution_authorized
    text=view.model_dump_json()
    assert all(secret not in text for secret in ('top-secret','other-secret','pay1','opponent-hand',s.state_hash()))
    opponent,_=rules_view(cards,printing,(a,s,result,'bob'))
    assert opponent.result_type=='unavailable' and not opponent.transition
    forged=result.model_copy(update={'status':'SUPPORTED_ILLEGAL'})
    with pytest.raises(ValueError): rules_view(cards,printing,(a,s,forged,'alice'))


def test_unknown_rules_source_is_stale_not_approval():
    cards=Cards(); cards.records['me01-131']['effect']='Changed'
    result,_=rules_view(cards,'me01-131')
    assert result.review_support=='STALE' and result.status=='UNSUPPORTED' and not result.execution_authorized


def test_source_change_during_build_discards_packet(setup,monkeypatch):
    sources,_=setup
    import pokelab.agent_context as module
    original=module.rules_view
    def changed(*args,**kwargs):
        result=original(*args,**kwargs)
        # Model an external concurrent change without writing through the builder.
        import os
        path=sources.paths['collection']; ns=path.stat().st_mtime_ns
        os.utime(path,ns=(ns,ns+1000000))
        return result
    monkeypatch.setattr(module,'rules_view',changed)
    packet=build(request(),sources)
    assert packet.status=='inconsistent_snapshot' and not packet.evidence


@pytest.mark.parametrize('n,prevalence,status',[(1,None,'insufficient_sample'),(14,None,'insufficient_sample'),(15,100.0,'observed')])
def test_prevalence_threshold_preserves_upstream_null(setup,n,prevalence,status):
    sources,research=setup; seed(research,[4]*n)
    competitive=payload(build(request(archetype=KEY),sources),'competitive')
    assert competitive.sample_size==n
    assert competitive.archetypes[0].prevalence_percent==prevalence
    assert competitive.archetypes[0].status==status


def test_rules_illegal_preview_derivation_and_private_dependencies():
    cards=Cards(); s=scenario()
    a=action(s,choices=paid(payment=('pay1','pay1'))); result=evaluate(a,s,cards)
    view,_=rules_view(cards,'me01-131',(a,s,result,'alice'))
    assert view.status=='SUPPORTED_ILLEGAL' and not view.execution_authorized
    from test_rules_foundation import instance as ab_instance
    from pokelab.rules import Scenario, RULESET, ODDISH, Action
    preview_state=Scenario(ruleset=RULESET,revision=0,players=('p1','p2'),turn_player='p1',
        isolation_confirmed=True,unresolved_dependencies=(),instances=(ab_instance('own','p1','active'),ab_instance('opp','p2','active')))
    a=Action(profile=ODDISH,actor='p1',source='own',target='opp',expected_revision=0,expected_state_hash=preview_state.state_hash())
    result=evaluate(a,preview_state,cards)
    view,_=rules_view(cards,'me02-001',(a,preview_state,result,'p1'))
    assert view.result_type=='preview' and view.status=='INSUFFICIENT_INFORMATION' and not view.execution_authorized
    assert 'energy-payment' in view.missing and 'weakness-resistance' in view.unsupported
    from test_rules_modifiers import state as modifier_state, action as modifier_action
    s=modifier_state(cards,2); a=modifier_action(s); result=evaluate(a,s,cards)
    view,_=rules_view(cards,'sv05-159',(a,s,result,'bob'))
    assert view.result_type=='derivation' and not view.execution_authorized
    assert 'concealed' not in view.model_dump_json() and s.state_hash() not in view.model_dump_json()
    s=scenario().model_copy(update={'unresolved_dependencies':('top-secret',)})
    a=action(s,choices=paid()); result=evaluate(a,s,cards)
    view,_=rules_view(cards,'me01-131',(a,s,result,'alice'))
    assert view.status=='UNSUPPORTED' and view.unsupported==('additional-private-or-unreviewed-dependency',)
    assert 'top-secret' not in view.model_dump_json()


def test_mixed_allocations_and_exact_finish_are_not_collapsed(setup):
    sources,research=setup
    with sqlite3.connect(sources.paths['workspace']) as db:
        doc=json.loads(db.execute('SELECT document FROM workspace').fetchone()[0])
        doc['dirty']=True
        doc['entries'][0]['allocations']=[dict(printing_id='sm2-1',variant='normal',quantity=2),
                                         dict(printing_id='sm2-1',variant='unspecified',quantity=2)]
        db.execute('UPDATE workspace SET revision=8,document=?',(json.dumps(doc),))
    before=sources.paths['workspace'].read_bytes()
    packet=build(request(variant='normal'),sources)
    assert payload(packet,'deck').selected_quantity==4 and payload(packet,'deck').dirty
    assert payload(packet,'ownership').exact[0].quantity==3
    assert payload(packet,'ownership').functional_total==5
    assert before==sources.paths['workspace'].read_bytes()


def test_readonly_connections_reject_sql_writes(setup):
    sources,_=setup
    with sources.snapshot() as (dbs,errors):
        assert not errors
        for db in dbs.values():
            with pytest.raises(sqlite3.OperationalError): db.execute('CREATE TABLE agent_must_not_write(x)')
