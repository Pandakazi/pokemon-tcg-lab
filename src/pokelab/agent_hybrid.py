"""Small, optional action-intent bridge. Never infer actions from prose."""
import json
import re
from .agent_deck_proposals import Candidate, Proposal

INSTRUCTIONS = '''
Respond in natural prose, not a JSON answer envelope. Zero artifacts is normal.
For a full deck, append exactly one structured block (never a prose deck list):
<POKELAB_ACTIONS>{"type":"generated_deck","name":"Deck concept","cards":[{"card_name":"Card name","quantity":1}]}</POKELAB_ACTIONS>
For changes to the active deck use:
<POKELAB_ACTIONS>{"type":"proposed_deck_changes","changes":[{"action":"add","card_name":"Card name","quantity":1}]}</POKELAB_ACTIONS>
These examples show shape, not a complete deck. FINALIZE requires exact cards totaling
60; no "or similar". A generated deck stays separate even when an active deck exists.
A draft may use role instead of card_name for an unresolved slot. Optional printing_id
must be an actual supplied printing, never invented. Positive integer quantities only.
Maximum 60 entries, 8192 bytes per block. Optional rationale is your tradeoff explanation;
optional fact_ids selects up to 12 exact evidence IDs for source display.
PokéLab owns quantities, subtotals, legality and validation; never claim a list passed.
When additions need space, propose balancing cuts in this same response. Preserve core
concept cards; prefer situational/redundant slots and explain the sacrifice. Never cut
an addition to cancel the user's requested increase. An explicit user cut owns the cut;
if impossible, explain it and discuss alternatives separately, not as accepted changes.
For 'those three', explicitly name the cards from recent structured artifacts/context.
If materially ambiguous, ask one concise question and emit no actions. No deck writes.
'''


def parse(text, active, metadata=None):
    """Salvage independent entries; ambiguous/multiple blocks are never merged."""
    start=text.find('<POKELAB_ACTIONS')
    prose=text if start<0 else text[:start]
    proposal=None;issues=[]
    if start<0:return prose.strip(),None,[]
    match=re.search(r'<POKELAB_ACTIONS>\s*(.*?)\s*</POKELAB_ACTIONS>',text,re.S)
    if not match or text.count('<POKELAB_ACTIONS')!=1:
        return prose.strip(),None,['action_summary_malformed']
    try:
        if len(match[1].encode())>8192:raise ValueError()
        data=json.loads(match[1])
        if not isinstance(data,dict):raise ValueError()
        kind=data.get('type')
        if kind not in (None,'generated_deck','proposed_deck_changes'):raise ValueError()
        if kind=='generated_deck':
            active=False
            if not isinstance(data.get('cards'),list):raise ValueError()
            data['changes']=[dict(item,action='add') if isinstance(item,dict) else item for item in data['cards']]
        if kind=='proposed_deck_changes' and not active:raise ValueError()
        if not isinstance(data.get('changes'),list):raise ValueError()
    except (ValueError,TypeError):return prose.strip(),None,['action_summary_malformed']
    if metadata is not None:
        refs=data.get('fact_ids',[])
        metadata['fact_ids']=[ref for ref in refs[:12] if isinstance(ref,str) and len(ref)<=160] if isinstance(refs,list) else []
    adds=[];removes=[]
    if len(data['changes'])>60:issues.append('action_summary_overflow')
    for index,item in enumerate(data['changes'][:60]):
        try:
            if not isinstance(item,dict) or item.get('action') not in ('add','remove'):raise ValueError()
            if not active and item['action']=='remove':raise ValueError()
            candidate=Candidate(name=item.get('card_name',''),printing_id=item.get('printing_id'),role=item.get('role',''),quantity=item.get('quantity'))
            if not candidate.name.strip() and not candidate.role.strip():raise ValueError()
            (adds if item['action']=='add' else removes).append(candidate)
        except (ValueError,TypeError):issues.append(f'action_{index+1}_unresolved')
    rationale=data.get('rationale','')
    if not isinstance(rationale,str):rationale=''
    if adds or removes:
        name=data.get('name','Experimental concept')
        if not isinstance(name,str) or len(name)>100:
            issues.append('artifact_name_invalid');name='Experimental concept'
        proposal=Proposal(kind='diff' if active else 'list',name=name,adds=tuple(adds) if active else (),
            removes=tuple(removes),cards=tuple(adds) if not active else (),rationale=rationale[:1000])
    else:issues.append('no_resolved_action_intent')
    return prose.strip(),proposal,issues


def explicit_cut(question):
    """Only a direct user cut command, never model prose or a hypothetical."""
    match=re.match(r"^\s*(?:please\s+)?(?:cut|remove)\s+(?:(\d+)\s+)?(.+?)(?=\s+and\s+|[.!?]|$)",question,re.I)
    if not match:return None
    try:return Candidate(name=match[2].strip(),quantity=int(match[1] or 1))
    except ValueError:return None
