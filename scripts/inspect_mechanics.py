"""Offline local Standard-corpus inspection; no retrieval or Agent integration."""
import argparse
from dataclasses import asdict
import gzip
import json
from pathlib import Path

from pokelab.mechanics_discovery import analyze, canonical, digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cards',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    summary,cards,effects,taxonomy=analyze(args.cards)
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    payload=''.join(canonical(asdict(e))+'\n' for e in effects).encode('utf-8')
    (output/'effects.jsonl.gz').write_bytes(gzip.compress(payload,mtime=0))
    (output/'cards.json.gz').write_bytes(gzip.compress(canonical(cards).encode('utf-8'),mtime=0))
    summary['effects_hash']=digest([asdict(e) for e in effects])
    summary['artifact_format']='gzip with mtime=0; UTF-8 JSONL effects, JSON cards; all selected printings retained'
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    examples=[]
    for status in ('unclassified','partial','missing'):
        unique={}
        for e in effects:
            if e.representation==status: unique.setdefault((e.component,e.normalized_text),e)
        examples += [asdict(e) for e in list(unique.values())[:12]]
    (output/'coverage-examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    counts={}
    for e in effects:
        if e.normalized_text: counts.setdefault(e.normalized_text,[]).append(e)
    rare=[dict(text=text,printing=items[0].printing,name=items[0].name,component=items[0].component,
        printings=len({e.printing for e in items}),mechanics=items[0].mechanics)
        for text,items in sorted(counts.items()) if len({e.functional_identity for e in items})==1]
    (output/'rare-effects.json').write_text(json.dumps(rare,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(canonical(dict(printings=len(cards),effects=len(effects),coverage=summary['coverage'],
        observed_concepts=len(summary['taxonomy_frequencies']),corpus_hash=summary['corpus_hash'])))


if __name__=='__main__': main()
