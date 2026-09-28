"""Offline evaluation; targets are manually specified source printings, not search output."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import socket

from pokelab.alternative_retrieval import RetrievalIndex
from pokelab.mechanics_discovery import analyze, digest


def evaluate(index,benchmark):
    printing_to_fid={c['printing']:c['functional_identity'] for c in index.cards}
    rows=[]
    for case in benchmark['cases']:
        reference=printing_to_fid[case['reference']] if case.get('reference') else None
        response=index.search(case['query'],reference,limit=50)
        results=response['results'];ids=[r['functional_identity'] for r in results]
        targets=[printing_to_fid[p] for p in case.get('targets',[])]
        ranks=[ids.index(fid)+1 if fid in ids else None for fid in targets]
        rows.append(dict(**case,target_ranks=ranks,
            hits={str(k):any(r is not None and r<=k for r in ranks) for k in (1,3,5,10)},
            total_candidates=response['total_candidates'],status=response['status'],
            top10=[dict(functional_identity=r['functional_identity'],name=r['name'],
                printing=r['representative']['printing'],classification=r['classification'],score=r['score'],
                score_components=r['score_components'],constraints_satisfied=r['constraints_satisfied'],
                constraints_unevaluable=r['constraints_unevaluable']) for r in results[:10]],
            reference_used=response['query']['reference_used'],limitations=response['limitations']))
    positive=[r for r in rows if r.get('targets')]
    pairs=[]
    for pair in benchmark['pairs']:
        a,b=[next(r for r in rows if r['id']==key) for key in pair]
        aa={r['functional_identity'] for r in a['top10']};bb={r['functional_identity'] for r in b['top10']}
        pairs.append(dict(cases=pair,top10_jaccard=len(aa&bb)/len(aa|bb) if aa|bb else 1,
            known_target_hit_consistent=a['hits']['10']==b['hits']['10']))
    return dict(version='pokelab-retrieval-evaluation-v1',corpus_hash=index.corpus_hash,
        benchmark_hash=digest(benchmark),case_count=len(rows),known_target_cases=len(positive),
        known_target_hit_counts={str(k):sum(r['hits'][str(k)] for r in positive) for k in (1,3,5,10)},
        interpretation='Any independently specified target in top K; not precision or full recall.',
        pairs=pairs,cases=rows)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',required=True)
    parser.add_argument('--benchmark',default='tests/fixtures/alternative_retrieval_benchmark.json')
    parser.add_argument('--output',default='docs/phase-7c3-retrieval/evaluation.json')
    args=parser.parse_args()
    def forbidden(*a,**kw): raise AssertionError('External network prohibited')
    socket.socket.connect=forbidden
    socket.socket.connect_ex=forbidden
    summary,cards,effects,_=analyze(args.database)
    index=RetrievalIndex(cards,effects,summary['corpus_hash'])
    benchmark=json.loads(Path(args.benchmark).read_text(encoding='utf-8'))
    result=evaluate(index,benchmark)
    # Exhaustive source-text reachability check across the current corpus. Exact
    # text eligibility is checked directly; representative full searches are in tests.
    result['safety']=dict(standard_printings=len(cards),functional_identities=len(index.groups),
        components=len(effects),text_components=sum(bool(e.normalized_text) for e in effects),
        text_functional_identities=len({e.functional_identity for e in effects if e.normalized_text}),
        taxonomy_free_text_components=sum(bool(e.normalized_text) and not e.mechanics for e in effects),
        partial_text_components=sum(bool(e.normalized_text) and e.representation=='partial' for e in effects),
        all_effects_indexed=len(index.effects)==len(effects),
        all_text_identities_indexed=all(e.functional_identity in index.groups for e in effects if e.normalized_text),
        all_sources_preserved=all(e.source_url and e.source_card_hash and e.checked_at for e in effects))
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))


if __name__=='__main__': main()
