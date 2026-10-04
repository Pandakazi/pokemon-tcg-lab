"""Transient Agent proposals over Deck Builder identities and validation. No writes.

The model proposes once. Local resolution returns corrections and ranked repair
options; it never invents a replacement, applies a diff, or calls another model.
"""
from copy import deepcopy
import json
import re
from typing import Literal

from pydantic import Field
from .agent_context_models import Frozen
from .decks import Decks, DeckProvider, deck_identity, check_allocations
from .engine import normalized_name
from .library_identity import BASIC_NAMES
from .quantities import variant_names
from .rules.models import digest


class Candidate(Frozen):
    name: str = Field(default='', max_length=100)
    printing_id: str | None = Field(default=None, max_length=100)
    quantity: int = Field(default=1, ge=1, le=999, strict=True)
    role: str = Field(default='', max_length=250)


class Premise(Frozen):
    name: str = Field(max_length=100, min_length=1)
    printing_id: str | None = Field(default=None, max_length=100)
    expected_text: str = Field(default='', max_length=1600)


class Proposal(Frozen):
    kind: Literal['list', 'diff']
    name: str = Field(default='Experimental concept', max_length=100)
    cards: tuple[Candidate, ...] = Field(default=(), max_length=100)
    adds: tuple[Candidate, ...] = Field(default=(), max_length=60)
    removes: tuple[Candidate, ...] = Field(default=(), max_length=60)
    rationale: str = Field(default='', max_length=1000)


def lifecycle(question):
    q=question.casefold()
    # Explicit partial intent wins over the word 60 in "not ready for a 60".
    if re.search(r'not ready|just.*(?:shell|core)|sketch|partial (?:list|deck)',q): return 'DRAFT'
    if re.search(r'finali[sz]|finished|give me (?:the |a )?60|resolve.*slots|tournament legal|ptcgl',q): return 'FINALIZE'
    if re.search(r'recommend.*(?:deck|list)|actually play|specific cards|exact cards|quantit|cut and add|remov.*add|cards.*change',q): return 'RECOMMEND'
    if re.search(r'\bshell\b|core look|draft',q): return 'DRAFT'
    return 'EXPLORE'


INSTRUCTIONS = """
Concrete-output extension: THE MODEL BUILDS IT. POKÉLAB VALIDATES IT.
The envelope's lifecycle is inferred, not a user mode. EXPLORE freely; DRAFT may
contain unresolved roles. RECOMMEND exact cards/changes; FINALIZE requests a complete
60 with no placeholders. The server, not you, decides validation/legality status.
Keep ordinary prose conversational. Never claim a list is validated/tournament
legal before local checks. Put exact list quantities in proposal, not in prose.
proposal is optional: {kind:"list" or "diff",name,cards,adds,removes,rationale}.
Each cards/adds/removes entry: {name,printing_id:null or exact local printing ID,
quantity:positive integer,role:strategic job}. Max 100 list rows, 60 add/remove rows.
A role-only entry with name:"" is an unresolved draft slot. For a list supply cards;
for an active-deck diff supply adds/removes only. Never pretend a proposal was saved.
You may nominate cards not pre-retrieved. Local resolution checks them afterwards.
For ambiguous names use a printing ID if known; never invent an ID to force a match.
Use the complete source active deck and actual quantities for cuts or "add another".
Preserve the user's concept and intended roles when correcting illegal suggestions.
premises is optional (max 12): {name,printing_id,expected_text}. Register named cards
whose exact effect materially drives advice, including matchup premises and specific
recommendations. expected_text is the exact printed effect you are relying on, if
known, NOT a remembered paraphrase. Wrong/unknown text is corrected locally.
Ordinary strategic reasoning needs neither a premise nor a legal 60. In paragraphs,
optional depends_on lists premise/card names when an argument depends on their facts.
Unresolved/illegal premises receive corrections, not silence. Separately discuss
quality vs legality; an Energy/evolution concern is advisory, not deck invalidity.
Do not repeat the full list in rationale or paragraphs. The UI renders canonical
resolved names/counts and validation. Return an incomplete proposal honestly rather
than filling roles with invented cards. No write actions, repair calls or browsing.
"""


def printed(raw):
    return {k:raw[k] for k in ('id','name','category','hp','stage','types','suffix','legal','evolveFrom','attacks','abilities','effect','energyType','rarity') if k in raw}


class Resolver:
    def __init__(self, collection, path):
        self.collection=collection
        self.provider=DeckProvider(collection)
        self.records=self.provider.records
        self.path=path
        self.index=None

    def resolve(self, candidate, active=None):
        if candidate.printing_id:
            record=self.records.get(candidate.printing_id)
            matches=[record] if record else []
            if record and candidate.name and normalized_name(record['card']['name'])!=normalized_name(candidate.name):
                return None,'name_printing_mismatch',[]
        else:
            name=normalized_name(candidate.name)
            energy=BASIC_NAMES.get(name)
            matches=[r for r in self.records.values() if r.get('game')!='pocket' and
                (normalized_name(r['card']['name'])==name or energy and deck_identity(r)=='deck-basic-energy:'+energy)]
        groups={}
        for record in matches: groups.setdefault(deck_identity(record),[]).append(record)
        if active and not candidate.printing_id:
            present={e['identity'] for e in active['entries']}
            chosen={k:v for k,v in groups.items() if k in present}
            if chosen: groups=chosen
        legal={k:v for k,v in groups.items() if self.provider.get(k)['card'].get('legal',{}).get('standard') is True}
        if len(groups)>1 and legal: groups=legal
        if len(groups)!=1:
            options=[self.view(sorted(v,key=lambda r:r['card']['id'])[0]) for _,v in sorted(groups.items())][:5]
            return None,'ambiguous' if groups else 'unresolved',options
        key,records=next(iter(groups.items()))
        record=sorted(records,key=lambda r:(r['card'].get('legal',{}).get('standard') is not True,r['card']['id']))[0]
        canonical=self.provider.get(key)
        standard=canonical['card'].get('legal',{}).get('standard')
        state='resolved' if standard is True and record.get('game')!='pocket' else 'illegal' if standard is False or record.get('game')=='pocket' else 'unknown_legality'
        return record,state,[]

    def view(self, record):
        raw=record['card'];key=deck_identity(record)
        return dict(card_id=key,printing_id=raw['id'],canonical_name=raw['name'],category=raw.get('category'),
            standard=self.provider.get(key)['card'].get('legal',{}).get('standard'),printed=printed(raw),
            checked_at=record.get('checked_at'),source='TCGdex',content_hash=digest(raw))

    def alternatives(self, role, original=None, *, exclude_ace=False):
        if not role and original is None:return []
        from .alternative_retrieval import RetrievalIndex
        if self.index is None:self.index=RetrievalIndex.from_database(self.path)
        # Accepted retrieval supplies mechanical candidates, never a strategic verdict.
        lookups=[('same_role',role)] if role else []
        if original:
            effects=[c.get('effect','') for k in ('abilities','attacks') for c in original['card'].get(k,[])]
            effects += [original['card'].get('effect','')]
            lookups += [('same_effect',s) for s in effects if s]
        q=role.casefold()
        aliases=[]
        if 'recover' in q:aliases=['recover Pokémon from discard pile','energy recovery']
        elif 'draw' in q:aliases=['draw']
        elif 'devol' in q:aliases=['devolution']
        elif 'mill' in q:aliases=['mill my opponent']
        lookups += [('same_function',q) for q in aliases]
        results=[];seen=set()
        for tier,query in lookups[:5]:
            for hit in self.index.search(query[:1000],limit=10)['results']:
                printing=hit['representative']['printing'];record=self.records.get(printing)
                if not record:continue
                key=deck_identity(record);raw=record['card']
                if exclude_ace and 'ACE SPEC' in raw.get('rarity','').upper():continue
                if key in seen or original and key==deck_identity(original):continue
                if self.provider.get(key)['card'].get('legal',{}).get('standard') is not True:continue
                if 'draw' in q and re.search(r'single.prize|not.*two prizes|won.t.*two prizes',q):
                    if raw.get('category')!='Pokemon' or raw.get('suffix') or re.search(r'\b(?:ex|V|VMAX|VSTAR|GX)\b',raw['name']):continue
                if re.search(r'low.commitment',q) and raw.get('category')=='Pokemon' and raw.get('stage')!='Basic':continue
                seen.add(key);results.append(dict(**self.view(record),tier=tier,
                    tradeoff='Mechanical candidate, not a proven equivalent; compare the printed conditions, setup and engine fit.'))
                if len(results)==3:return results
        return results


def diagnostics(rows):
    """Printed-only advisory checks, no simulated Energy engine or matchup rating."""
    notes=[];names={normalized_name(r['canonical_name']) for r in rows}
    energy={}
    special=False
    for row in rows:
        key=row['card_id']
        if key.startswith('deck-basic-energy:'):energy[key.split(':',1)[1]]=energy.get(key.split(':',1)[1],0)+row['quantity']
        elif row['category']=='Energy':special=True
    for row in rows:
        raw=row['printed'];name=row['canonical_name']
        if raw.get('evolveFrom') and normalized_name(raw['evolveFrom']) not in names:
            notes.append(f"{name}'s printed evolution predecessor {raw['evolveFrom']} is absent. Check the evolution plan or an explicit alternate route; this is a strategic warning, not a legality failure.")
        for component in raw.get('abilities',[]):
            text=component.get('effect','')
            if re.search(r'(?:Darkness|\{D\}) Energy attached',text,re.I) and not energy.get('Darkness'):
                notes.append(f"{name} / {component.get('name','Ability')}: no Basic Darkness source is present for the printed attachment condition. {'Special Energy compatibility needs review.' if special else 'No usable Darkness source is established.'} Add a compatible source or replace this role.")
        for attack in raw.get('attacks',[]):
            cost=attack.get('cost',[])
            if len(cost)>sum(energy.values()) and not special:
                notes.append(f"{name} / {attack.get('name','attack')} has a printed cost of {len(cost)} Energy, above this list's {sum(energy.values())} Basic Energy cards. Review the Energy package or an explicit cost-reduction route.")
    return list(dict.fromkeys(notes))[:12]


def evaluate(proposal, premises, sources, request, envelope):
    from .agent_context_sources import SnapshotCards, SnapshotCollection, stamp
    report=dict(version='pokelab-proposal-v1',status='PROPOSED',lifecycle=envelope['lifecycle'],
        format='standard',kind=proposal.kind if proposal else 'premises',name=proposal.name if proposal else '',
        deck_id=None,source_revision=request.revision if request.include_deck else None,
        source_content_hash=None,validation_status='UNRESOLVED',legality_status='UNRESOLVED',
        resolution_status='RESOLVED',cards=[],adds=[],removes=[],unresolved=[],premises=[],
        total_cards=0,hard_validation=[],strategic_diagnostics=[],repair_notes=[],alternatives=[],
        rationale=proposal.rationale if proposal else '',writes_performed=False)
    rejected=set();new_evidence=[]
    with sources.snapshot() as (dbs,errors):
        if 'cards' in errors:
            report['repair_notes'].append('Local card data is unavailable. Keep this as a concept; no concrete list can be verified yet.')
            return report,new_evidence,{p.name for p in premises}
        cards=SnapshotCards(sources.paths['cards'],dbs['cards'])
        # catalog() is read-only; collection tables are not required to resolve facts.
        collection=SnapshotCollection(cards,sources.paths['collection'],dbs.get('collection'))
        resolver=Resolver(collection,sources.paths['cards'])
        active=None
        if request.include_deck:
            row=None if 'workspace' in errors else dbs['workspace'].execute('SELECT revision,document FROM workspace WHERE id=1').fetchone()
            if row is None or row['revision']!=request.revision:
                report.update(validation_status='STALE',legality_status='UNRESOLVED')
                report['repair_notes'].append('The active deck changed while I was considering this. These changes are not validated against the current revision; review the new snapshot first.')
                return report,new_evidence,{p.name for p in premises}
            active=json.loads(row['document']);check_allocations(active)
            report.update(deck_id=active['id'],source_content_hash=digest(active))
        if envelope.get('card_source_stamp')!=digest(stamp(sources.paths['cards'])):
            report['repair_notes'].append('Card data changed during this response; concrete recommendations need a fresh snapshot.')
            report['validation_status']='STALE'
            return report,new_evidence,{p.name for p in premises}

        def evidence(record):
            raw=record['card'];item=dict(id='card-'+digest(raw)[:24],kind='fact',title=raw['name'],printing=raw['id'],
                value=printed(raw),source='TCGdex',checked_at=record.get('checked_at'),content_hash=digest(raw))
            if not any(e['id']==item['id'] for e in new_evidence):new_evidence.append(item)

        def resolve(candidate, cutting=False):
            record,state,choices=resolver.resolve(candidate,active if cutting else None)
            if record:evidence(record)
            if state!='resolved' and not (cutting and record is not None and state in ('illegal','unknown_legality')):
                label=candidate.name or candidate.role or 'Unresolved slot'
                rejected.add(candidate.name)
                report['unresolved'].append(dict(name=label,quantity=candidate.quantity,role=candidate.role,state=state))
                if len(report['alternatives'])<8:
                    options=choices or resolver.alternatives(candidate.role,record)
                    report['alternatives'].append(dict(for_card=label,role=candidate.role,candidates=options))
                report['repair_notes'].append(f"{label}: {'several different printed versions match; choose the intended one' if state=='ambiguous' else 'not established as a current legal card for this role'}. Keep the role; review the local alternatives instead of treating this as finished.")
            return record,state

        for premise in premises:
            record,state=resolve(Candidate(name=premise.name,printing_id=premise.printing_id))
            entry=dict(name=premise.name,status=state,card=resolver.view(record) if record else None)
            if record and premise.expected_text:
                text=' '.join(c.get('effect','') for k in ('attacks','abilities') for c in record['card'].get(k,[]))+' '+record['card'].get('effect','')
                if normalized_name(premise.expected_text) not in normalized_name(text):
                    entry['status']='corrected';rejected.add(premise.name)
                    report['repair_notes'].append(f"I was relying on unverified text for {premise.name}. The local printed effect below is the basis to use instead; the dependent plan needs reconsideration.")
            report['premises'].append(entry)

        if not proposal:
            report['validation_status']='REVIEWED';return report,new_evidence,rejected
        document=deepcopy(active) if proposal.kind=='diff' and active else dict(id='proposal',name=proposal.name,format='standard',entries=[],has_saved=True,dirty=True)
        if proposal.kind=='diff' and active is None:
            report['hard_validation'].append('A proposed change needs the exact active deck revision. No cuts or additions were applied.')
        if (proposal.kind=='list' and (proposal.adds or proposal.removes)) or (proposal.kind=='diff' and proposal.cards):
            report['hard_validation'].append('The proposal mixes list and change formats. Keep the concept, but separate the proposed list from add/cut instructions.')
        for candidate in proposal.removes if proposal.kind=='diff' and active else ():
            record,state=resolve(candidate,True)
            if not record:continue
            key=deck_identity(record);entry=next((e for e in document['entries'] if e['identity']==key),None)
            original=next((e for e in active['entries'] if e['identity']==key),None)
            valid=entry is not None and entry['quantity']>=candidate.quantity
            report['removes'].append(dict(**resolver.view(record),quantity=candidate.quantity,current_quantity=original['quantity'] if original else 0,validated=valid))
            if not valid:
                report['hard_validation'].append(f"I cannot cut {candidate.quantity} {candidate.name}: the source revision has {original['quantity'] if original else 0}, or earlier proposed cuts already use them.")
                report['repair_notes'].append('Keep the existing card; choose a cut from the actual source list. No alternative cut has been silently substituted.')
                alternatives=[dict(card_id=e['identity'],name=e.get('name'),current_quantity=e['quantity']) for e in active['entries']][:8]
                report['alternatives'].append(dict(for_card=candidate.name,role='choose a cut from the source revision',source_candidates=alternatives))
                continue
            left=candidate.quantity
            for allocation in list(entry['allocations']):
                take=min(left,allocation['quantity']);allocation['quantity']-=take;left-=take
                if not allocation['quantity']:entry['allocations'].remove(allocation)
                if not left:break
            entry['quantity']-=candidate.quantity
            if not entry['quantity']:document['entries'].remove(entry)
        for candidate in proposal.cards if proposal.kind=='list' else proposal.adds:
            record,state=resolve(candidate)
            if record is None:continue
            key=deck_identity(record);raw=record['card'];view=resolver.view(record)
            original=next((e for e in (active or {}).get('entries',[]) if e['identity']==key),None)
            if proposal.kind=='diff':report['adds'].append(dict(**view,quantity=candidate.quantity,current_quantity=original['quantity'] if original else 0,role=candidate.role))
            entry=next((e for e in document['entries'] if e['identity']==key),None)
            if entry is None:
                entry=dict(identity=key,name=raw['name'],category=raw['category'],quantity=0,allocations=[]);document['entries'].append(entry)
            variants=variant_names(raw,());variant='normal' if 'normal' in variants else sorted(variants)[0]
            allocation=next((a for a in entry['allocations'] if a['printing_id']==raw['id'] and a['variant']==variant),None)
            if allocation is None:allocation=dict(printing_id=raw['id'],variant=variant,quantity=0);entry['allocations'].append(allocation)
            allocation['quantity']+=candidate.quantity;entry['quantity']+=candidate.quantity
        for entry in document['entries']:
            record=resolver.records.get(entry['allocations'][0]['printing_id'])
            if record:report['cards'].append(dict(**resolver.view(record),quantity=entry['quantity']))
        document['has_saved']=report['lifecycle'] in ('RECOMMEND','FINALIZE')
        validation=Decks(collection,sources.paths['workspace']).validation(document)
        report['hard_validation']+=validation['reasons']+validation['unknown']
        report['limitations']=validation['limitations'];report['total_cards']=validation['total']
        report['strategic_diagnostics']=diagnostics(report['cards'])
        report['resolution_status']='UNRESOLVED' if report['unresolved'] else 'RESOLVED'
        report['legality_status']='INVALID' if validation['reasons'] else 'UNKNOWN' if validation['unknown'] or report['unresolved'] else 'INCOMPLETE' if validation['total']!=60 else 'LEGAL_SUPPORTED_CHECKS'
        report['validation_status']='NEEDS_REPAIR' if report['hard_validation'] or report['unresolved'] else 'PARTIAL' if validation['total']!=60 else 'VALIDATED'
        if report['lifecycle']=='DRAFT' and validation['total']<60:
            report['repair_notes'].append('This is a partial shell, not a finished 60. Unresolved roles are deliberate slots until a later finalize request.')
        if validation['reasons']:
            report['repair_notes'].append('The concept can continue. Resolve the construction issues below before calling this a finished list; strategic warnings remain separate.')
        ace=[r for r in report['cards'] if 'ACE SPEC' in r['printed'].get('rarity','').upper()]
        if sum(r['quantity'] for r in ace)>1:
            keep=ace[0]
            anchor=next((c for c in (*proposal.cards,*proposal.adds) if c.name==keep['canonical_name'] or c.printing_id==keep['printing_id']),None)
            reason=f"to preserve the proposed {anchor.role} role" if anchor and anchor.role else 'as the first proposed anchor, subject to your strategic priorities'
            report['repair_notes'].append(f"Keep one {keep['canonical_name']} {reason}; replace the other ACE SPEC slots while preserving their roles. This is a proposed choice, not a silent list edit.")
            for row in ace[1:]:
                candidate=next((c for c in (*proposal.cards,*proposal.adds) if c.name==row['canonical_name'] or c.printing_id==row['printing_id']),None)
                options=resolver.alternatives(candidate.role if candidate else '',resolver.records[row['printing_id']],exclude_ace=True)
                report['alternatives'].append(dict(for_card=row['canonical_name'],role=candidate.role if candidate else '',candidates=[r for r in options if 'ACE SPEC' not in r['printed'].get('rarity','').upper()]))
        return report,new_evidence,rejected
