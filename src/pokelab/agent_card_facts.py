"""Bounded named factual-clause reconciliation, not general claim verification."""
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


def reconcile(text, sources, request, envelope, corrections=None):
    matches=[];sentence_end=-1
    for match in CLAIM.finditer(text):
        if match.start()<sentence_end:continue
        matches.append(match)
        end=re.search(r'[.!?\n]',text[match.end():])
        sentence_end=match.end()+end.start()+1 if end else len(text)
        if len(matches)==12:break
    if not matches:return text,[]
    facts=[]
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
            # Work backwards to keep character offsets stable. One sentence/clause
            # replacement does not remove adjacent strategic sentences.
            boundary=len(text)
            for match in reversed(matches):
                if match.start()>=boundary:continue
                name=match[1];verb=match[2]
                start=max(text.rfind(delimiter,0,match.start()) for delimiter in '.!?\n')+1
                while start<match.start() and text[start].isspace():start+=1
                # An embedded component name is not a new card subject. Prefer
                # a real card named earlier in this sentence, if unambiguous.
                if resolver and start<match.start():
                    prefix=text[start:match.start()]
                    names={r['card']['name'] for r in resolver.records.values() if re.search(r'(?<!\w)'+re.escape(r['card']['name'])+r'(?!\w)',prefix,re.I)}
                    if names:name=max(names,key=len)
                end=re.search(r'[.!?\n]',text[match.end():])
                stop=match.end()+end.start() if end else len(text)
                clause=text[start:stop]
                tail=re.split(r'\s+(?:so|therefore|because|which means)\s+',clause,maxsplit=1,flags=re.I)
                strategy=(' The strategic suggestion remains a hypothesis to reassess: '+tail[1]) if len(tail)==2 else ''
                if strategy and re.search(r'\d|\b(?:per Energy|discard requirements?|knockout threshold)\b',strategy,re.I):
                    strategy=' The exact damage or resource calculation still needs verification.'
                record=None;state='unavailable';parts=[];components=[]
                if resolver:
                    # Exact active allocations outrank catalogue representative selection.
                    entries=[e for e in (active or {}).get('entries',[]) if e.get('name','').casefold()==name.casefold()]
                    records=[resolver.records[a['printing_id']] for e in entries for a in e['allocations'] if a['printing_id'] in resolver.records]
                    signatures={digest(printed(r['card'])) for r in records}
                    if records:
                        # IDs alone must not turn mechanically identical allocations ambiguous.
                        signatures={digest({k:v for k,v in printed(r['card']).items() if k!='id'}) for r in records}
                        record=records[0] if len(signatures)==1 else None
                        state='resolved' if record else 'ambiguous'
                    else:record,state,_=resolver.resolve(Candidate(name=name))
                if not record:
                    reason='multiple materially different versions remain possible' if state=='ambiguous' else 'the exact local printed facts are unavailable for this snapshot'
                    correction=f"I cannot verify the exact printed details for {name}: {reason}. That specific factual premise is unresolved"
                else:
                    raw=record['card'];parts=[]
                    components=[]
                    if verb in ('uses','attacks with','requires','costs') or 'attack' in verb:
                        components=raw.get('attacks',[])
                    elif verb.startswith('has') or 'Ability' in verb or verb=='gives':
                        components=raw.get('abilities',[])
                    else:components=[*raw.get('abilities',[]),*raw.get('attacks',[])]
                    named=[c for c in components if c.get('name') and c['name'].casefold() in clause.casefold()]
                    if named:components=named
                    for component in components:
                        detail=component.get('effect') or 'exact effect text is unavailable locally'
                        cost=component.get('cost')
                        if cost is not None:detail+=f" Printed cost: {', '.join(cost) or 'none'}."
                        if component.get('damage') is not None:detail+=f" Printed damage: {component['damage']}."
                        parts.append(f"{component.get('name','Unnamed component')}: {detail}")
                    if raw.get('effect'):parts.append(raw['effect'])
                    if verb=='evolves from':parts=[f"printed evolution predecessor: {raw.get('evolveFrom','not established locally')}"]
                    if verb.startswith('is '):parts=[f"cached Standard legality: {raw.get('legal',{}).get('standard','unknown')}; this is not a live tournament ruling"]
                    correction=f"{raw['name']}: "+'; '.join(parts) if parts else f"I cannot verify the exact printed effect for {raw['name']} in this snapshot"
                    if verb in ('blocks','prevents'):
                        correction+=' The specific interaction is not established by printed text alone; a reviewed ruling may be needed'
                    facts.append(dict(id='card-'+digest(raw)[:24],kind='fact',title=raw['name'],printing=raw['id'],value=printed(raw),source='TCGdex',checked_at=record.get('checked_at'),content_hash=digest(raw)))
                unresolved=record is None or not parts or any(not c.get('effect') for c in components)
                # Only immediately attached dependent precision is affected. Keep
                # later strategic discussion; do not infer interactions from text.
                if unresolved:
                    remainder=text[stop:]
                    dependent=re.match(r'[.!?]\s+((?:It|This attack|That attack|This means|That means|You must|You can)\b[^.!?\n]*[.!?])',remainder,re.I)
                    while dependent and re.search(r'\d|discard|per Energy|knockout|damage',dependent[1],re.I):
                        stop+=dependent.end()
                        remainder=text[stop:]
                        dependent=re.match(r'\s*((?:It|This attack|That attack|This means|That means|You must|You can)\b[^.!?\n]*[.!?])',remainder,re.I)
                    if stop>match.end() and not text[stop:stop+1] in '.!?':
                        correction=correction.rstrip('.')+'.'
                correction=re.sub(r'([.!?])\1+',r'\1',' '.join(correction.split())).rstrip('.')
                if corrections is not None:corrections.append(correction)
                replacement=correction+strategy
                if text[stop:stop+1] not in ('.','!','?'):replacement=replacement.rstrip('.')+'.'
                text=text[:start]+replacement+text[stop:]
                boundary=start
    except (OSError,ValueError,KeyError,sqlite3.Error):
        # Storage/shape loss is not a reason to suppress the conversation.
        return text+' Exact named-card facts could not be refreshed locally; treat those premises as unverified.',[]
    return text,facts
