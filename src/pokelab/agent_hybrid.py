"""Small, optional action-intent bridge. Never infer actions from prose."""
import json
import re
from .agent_deck_proposals import Candidate, Proposal, quantity_claim

INSTRUCTIONS = '''
Answer in natural conversational prose, NOT a JSON answer object. Preserve strategic
reasoning. Recommendations need no tournament proof, creator intent or matchup.
Put reasoning in separate sentences from quantity/action instructions so PokéLab can
replace state assertions with checked counts without losing your explanation.
For concrete changes, append one hidden block:
<POKELAB_ACTIONS>{"changes":[{"action":"add","card_name":"Card name","quantity":1}]}</POKELAB_ACTIONS>
Each change has action add/remove, card_name or role, and a positive integer quantity
delta. Never provide IDs, current/resulting counts, revisions, legality or evidence.
Optional rationale is a short strategic hypothesis; confidence may be hypothesis or
recommendation. At most 60 changes and 8192 bytes in this optional JSON block.
With an active deck, changes are a proposed diff. Without one, add entries describe
a proposed list; remove entries cannot be resolved. DRAFT may leave role-only slots.
RECOMMEND encourages actions; FINALIZE needs complete resolvable intent before the
list can be called finished. No automatic changes, writes or retries occur.
Missing/uncertain replacements should be roles, never invented names or X-or-Y cards.
'''


def parse(text, active):
    """Salvage independent entries; ambiguous/multiple blocks are never merged."""
    start=text.find('<POKELAB_ACTIONS')
    prose=text if start<0 else text[:start]
    proposal=None;issues=[]
    if start<0:return prose.strip(),None,['action_summary_missing']
    match=re.search(r'<POKELAB_ACTIONS>\s*(.*?)\s*</POKELAB_ACTIONS>',text,re.S)
    if not match or text.count('<POKELAB_ACTIONS')!=1:
        return prose.strip(),None,['action_summary_malformed']
    try:
        if len(match[1].encode())>8192:raise ValueError()
        data=json.loads(match[1])
        if not isinstance(data,dict) or not isinstance(data.get('changes'),list):raise ValueError()
    except (ValueError,TypeError):return prose.strip(),None,['action_summary_malformed']
    adds=[];removes=[]
    if len(data['changes'])>60:issues.append('action_summary_overflow')
    for index,item in enumerate(data['changes'][:60]):
        try:
            if not isinstance(item,dict) or item.get('action') not in ('add','remove'):raise ValueError()
            if not active and item['action']=='remove':raise ValueError()
            candidate=Candidate(name=item.get('card_name',''),role=item.get('role',''),quantity=item.get('quantity'))
            if not candidate.name.strip() and not candidate.role.strip():raise ValueError()
            (adds if item['action']=='add' else removes).append(candidate)
        except (ValueError,TypeError):issues.append(f'action_{index+1}_unresolved')
    rationale=data.get('rationale','')
    if not isinstance(rationale,str):rationale=''
    if adds or removes:
        proposal=Proposal(kind='diff' if active else 'list',adds=tuple(adds) if active else (),
            removes=tuple(removes),cards=tuple(adds) if not active else (),rationale=rationale[:1000])
    else:issues.append('no_resolved_action_intent')
    return prose.strip(),proposal,issues


def strategic_prose(text, empirical, has_report=True):
    """Reconcile state-bearing sentences, not a prose-to-action parser.

    Retain separate strategic sentences and causal tails. No action is created here.
    Exact action/state wording is replaced by the canonical diff rendered elsewhere.
    """
    kept=[];qualified=False
    for sentence in re.split(r'(?<=[.!?])\s+|\n+',text):
        sentence=sentence.strip()
        if not sentence:continue
        if empirical.search(sentence):qualified=True;continue
        state=quantity_claim(sentence) or re.search(r'\b(?:legal|illegal|validated|deck size|copy limit|contains|deck has|deck includes)\b',sentence,re.I) or (has_report and re.search(r'\b(?:add|remove|cut|swap|replace)\b',sentence,re.I))
        if state:
            tail=re.split(r'\bbecause\b',sentence,maxsplit=1,flags=re.I)
            if len(tail)==2 and not quantity_claim(tail[1]) and not re.search(r'\b(?:legal|illegal|contains|has|copy limit)\b',tail[1],re.I):
                kept.append('My strategic reasoning: '+tail[1].strip())
            continue
        kept.append(sentence)
    return kept,qualified
