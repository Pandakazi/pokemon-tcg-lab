"""Typed printed-fact review. Never rewrite model prose or infer deck inventory."""
import json
import re
import sqlite3
from .agent_deck_proposals import Candidate, Resolver, printed
from .agent_context_sources import SnapshotCards, SnapshotCollection, stamp
from .rules.models import digest

# A casual card mention alone never opens a resolution snapshot.
CLAIM = re.compile(r"\b([A-Z][\w’'-]*(?: (?:[A-Z][\w’'-]*|ex)){0,4})(?:'s|’s)?\s+"
    r"(uses|attacks with|has (?:an? )?(?:Ability|attack)|gives|recovers|retrieves|"
    r"discards|draws|heals|blocks|prevents|requires|costs|evolves from|"
    r"is (?:legal|illegal)|(?:Ability|attack)\b)")


def review(text, sources, request, envelope):
    matches=[];sentence_end=-1
    for match in CLAIM.finditer(text):
        if match[1].split()[0].casefold() in {'that','this','it','they','those','these','setup','strategy'}:continue
        if match.start()<sentence_end:continue
        matches.append(match)
        end=re.search(r'[.!?\n]',text[match.end():])
        sentence_end=match.end()+end.start()+1 if end else len(text)
        if len(matches)==12:break
    if not matches:return [],[]
    facts=[];reviews=[]
    artifact=envelope.get('resolution_artifact') or envelope.get('artifacts',{}).get('generated_deck',{}).get('report',{})
    unresolved={row['name'].casefold() for row in artifact.get('unresolved',[]) if row.get('name')}
    resolved={row['canonical_name'].casefold():row['printing_id'] for row in artifact.get('cards',[])}
    try:
        with sources.snapshot() as (dbs,errors):
            fresh='cards' not in errors and digest(stamp(sources.paths['cards']))==envelope.get('card_source_stamp')
            active=None
            if request.include_deck:
                row=None if 'workspace' in errors else dbs['workspace'].execute('SELECT revision,document FROM workspace WHERE id=1').fetchone()
                fresh=fresh and row is not None and row['revision']==request.revision
                if fresh:active=json.loads(row['document'])
            resolver=None
            if fresh:
                cards=SnapshotCards(sources.paths['cards'],dbs['cards'])
                resolver=Resolver(SnapshotCollection(cards,sources.paths['collection'],dbs.get('collection')),sources.paths['cards'])
            for match in matches:
                name=match[1];verb=match[2]
                if name.casefold() in unresolved:
                    reviews.append(dict(card=name,status='unresolved',references=[]));continue
                start=max(text.rfind(delimiter,0,match.start()) for delimiter in '.!?\n')+1
                while start<match.start() and text[start].isspace():start+=1
                # An embedded component name is not a new card subject. Prefer
                # a real card named earlier in this sentence, if unambiguous.
                if resolver and start<match.start():
                    prefix=text[start:match.start()]
                    names={r['card']['name'] for r in resolver.records.values() if re.search(r'(?<!\w)'+re.escape(r['card']['name'])+r'(?!\w)',prefix,re.I)}
                    if names:name=max(names,key=len)
                if name.casefold() in unresolved:
                    reviews.append(dict(card=name,status='unresolved',references=[]));continue
                end=re.search(r'[.!?\n]',text[match.end():])
                stop=match.end()+end.start() if end else len(text)
                clause=text[start:stop]
                record=None;has_facts=False
                if resolver:
                    # Exact active allocations outrank catalogue representative selection.
                    entries=[e for e in (active or {}).get('entries',[]) if e.get('name','').casefold()==name.casefold()]
                    records=[resolver.records[a['printing_id']] for e in entries for a in e['allocations'] if a['printing_id'] in resolver.records]
                    signatures={digest(printed(r['card'])) for r in records}
                    if name.casefold() in resolved:
                        record,state,_=resolver.resolve(Candidate(name=name,printing_id=resolved[name.casefold()]))
                        if state!='resolved':record=None
                    elif records:
                        # IDs alone must not turn mechanically identical allocations ambiguous.
                        signatures={digest({k:v for k,v in printed(r['card']).items() if k!='id'}) for r in records}
                        record=records[0] if len(signatures)==1 else None
                        state='resolved' if record else 'ambiguous'
                    else:record,state,_=resolver.resolve(Candidate(name=name))
                if record:
                    raw=record['card']
                    components=[]
                    if verb in ('uses','attacks with','requires','costs') or 'attack' in verb:
                        components=raw.get('attacks',[])
                    elif verb.startswith('has') or 'Ability' in verb or verb=='gives':
                        components=raw.get('abilities',[])
                    else:components=[*raw.get('abilities',[]),*raw.get('attacks',[])]
                    named=[c for c in components if c.get('name') and c['name'].casefold() in clause.casefold()]
                    if named:components=named
                    has_facts=bool(raw.get('effect') or any(component.get('effect') or component.get('damage') is not None or component.get('cost') is not None for component in components))
                    if verb=='evolves from':has_facts=bool(raw.get('evolveFrom'))
                    if verb.startswith('is '):has_facts=raw.get('legal',{}).get('standard') is not None
                    facts.append(dict(id='card-'+digest(raw)[:24],kind='fact',title=raw['name'],printing=raw['id'],value=printed(raw),source='TCGdex',checked_at=record.get('checked_at'),content_hash=digest(raw)))
                reviews.append(dict(card=name,status='printed_reference' if record and has_facts else 'unresolved',
                    references=[f['id'] for f in facts if f['title']==name],
                    rules_boundary='printed_text_not_ruling' if verb in ('blocks','prevents') else None))
    except (OSError,ValueError,KeyError,sqlite3.Error):
        return [dict(status='unavailable',references=[])],[]
    return reviews,facts
