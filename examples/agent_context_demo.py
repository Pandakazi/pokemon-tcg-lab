"""Explicit-path, no-LLM Phase 7A acceptance demo. Never initializes storage."""
import argparse
from datetime import date
from hashlib import sha256
import json
import math
from pathlib import Path
import socket
import sqlite3

from pokelab.agent_context import build, canonical
from pokelab.agent_context_models import Request
from pokelab.agent_context_sources import Sources
from pokelab.rules.models import digest


def hashes(paths):
    result={}
    for path in paths:
        for candidate in (path,Path(str(path)+'-wal'),Path(str(path)+'-shm'),Path(str(path)+'-journal')):
            if candidate.exists():
                with candidate.open('rb') as stream:
                    h=sha256()
                    for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
                result[str(candidate)]=h.hexdigest()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('cards','collection','workspace','competitive'): parser.add_argument('--'+key,required=True)
    args=parser.parse_args(); sources=Sources(**vars(args))
    before=hashes(sources.paths.values())
    calls={'network':0,'writable_connections':0}
    connect=sqlite3.connect; network_connect=socket.socket.connect
    def readonly(path,*a,**kw):
        if '?mode=ro' not in str(path) or not kw.get('uri'):
            calls['writable_connections']+=1; raise AssertionError('Writable connection forbidden')
        return connect(path,*a,**kw)
    def no_network(*a,**kw):
        calls['network']+=1; raise AssertionError('Network forbidden')
    sqlite3.connect=readonly; socket.socket.connect=no_network
    try:
        request=Request(question='How common is Ultra Ball in the cached evidence, how does my active deck compare, and what can PokéLab establish about its effect?',
            printing='me01-131',as_of=date(2026,9,25),window='30',archetype='780e0eca3a75532945bfca1e',
            observation='15b36abbeb924e9b147771f2')
        packet=build(request,sources)
        assert packet.status=='ready',packet.coverage
        assert packet==build(request,sources),'Non-deterministic packet'
        data=packet.model_dump(mode='json'); data.pop('content_hash')
        assert packet.content_hash==digest(data)
        assert packet.budget.serialized_bytes==len(canonical(packet).encode())<=24576
        assert packet.budget.estimated_tokens==math.ceil(packet.budget.serialized_bytes/4)
        by_kind={e.payload.kind:e.payload for e in packet.evidence}
        rules=by_kind['rules']
        assert rules.review_support=='REVIEWED' and rules.result_type=='profile-only'
        assert rules.status=='INSUFFICIENT_INFORMATION' and not rules.execution_authorized
        assert by_kind['competitive'].period_start=='2026-08-27'
        ids={r.id for r in packet.references}
        assert all(set(e.references)<=ids for e in packet.evidence)
    finally:
        sqlite3.connect=connect; socket.socket.connect=network_connect
    after=hashes(sources.paths.values())
    assert before==after,'Database or sidecar hashes changed'
    assert calls=={'network':0,'writable_connections':0}
    print('PHASE 7A DEMO — NOT PM CERTIFICATION')
    print('REQUEST\n'+json.dumps(request.model_dump(mode='json'),indent=2,ensure_ascii=False))
    print('PACKET\n'+json.dumps(dict(version=packet.schema_version,hash=packet.content_hash,
        bytes=packet.budget.serialized_bytes,estimated_tokens=packet.budget.estimated_tokens,evidence_items=len(packet.evidence)),indent=2))
    for key,label in (('card','SELECTED CARD'),('deck','ACTIVE DECK'),('ownership','COLLECTION'),
                      ('competitive','COMPETITIVE EVIDENCE'),('observation','TOURNAMENT REFERENCE'),('rules','RULES')):
        print(label+'\n'+json.dumps(by_kind[key].model_dump(mode='json'),indent=2,ensure_ascii=False))
    print('PROVENANCE\n'+json.dumps(dict(all_references_resolve=True,references=[r.model_dump(mode='json') for r in packet.references]),indent=2,ensure_ascii=False))
    print('BUDGET\n'+json.dumps(dict(**packet.budget.model_dump(),omissions=packet.coverage.omitted),indent=2))
    print('SAFETY\nZero model/API calls; zero writable connections; database and sidecar hashes unchanged.')
    print('PASS 7A DEMO — NOT PM CERTIFICATION')


if __name__=='__main__': main()
