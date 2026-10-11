"""Conversation-only generated-deck referents. Never mutate workspace state."""
from copy import deepcopy
import re
from .rules.models import digest
from .agent_deck_proposals import Candidate, Proposal, lifecycle


def read_only(question):
    return bool(re.match(r'\s*(?:why\b|explain\b|critique\b|analy[sz]e\b|compare\b|what do you think\b|what are (?:the |its )?(?:weak|strength)|how (?:does|do|would)\b)',question,re.I))


def intent(question, history):
    if not history.get('artifacts', {}).get('generated_deck'):return None
    q=question.casefold()
    if history.get('artifacts',{}).get('deck_referent') in ('active','other') and not re.search(r'generated|your (?:own )?deck',q):return None
    if re.search(r'\b(?:active|saved|deck builder) deck\b|\b(?:new|different|another) deck\b|change (?:the )?subject|different topic|forget (?:that|this) deck|(?:this|selected) card\b',q):return None
    if read_only(question):return 'DISCUSS'
    if re.search(r'\b(?:make|apply) (?:those|these|the|your) (?:changes|recommendations)|\b(?:do|try) that\b|\bshow.*updated.*list',q):return 'APPLY'
    if re.search(r'\b(?:build|modify) (?:this|that|the current)\b|\bswap in\b|\bwork .+ into (?:this|that)\b',q):return 'RECOMMEND'
    if lifecycle(question)=='FINALIZE':return None
    if re.search(r'exact changes|cut and add|more aggressive|what would you change|try a control|\b(?:add|cut|replace|modify)\b',q) or lifecycle(question)=='RECOMMEND':return 'RECOMMEND'
    if re.search(r'\b(?:deck|list|critique|weaknesses|weakest|ratios|pilot|play|weak points|game plan|these cards|it|this|that|evidence|sources)\b',q):return 'DISCUSS'
    return 'DISCUSS'


def compose(artifact, proposal):
    """Bind functional IDs, reject phantom/excess cuts, retain every other slot."""
    report=artifact['report'];sandbox=report.get('candidate_sandbox') or {}
    allowed={r['candidate_id']:r for r in sandbox.get('candidates',[])}
    rows={r['candidate_id']:deepcopy(r) for r in report['cards']}
    counts={key:r['quantity'] for key,r in rows.items()}
    for group in ('removes','adds'):
        for c in getattr(proposal,group):
            source=rows.get(c.candidate_id) if group=='removes' else None
            item=allowed.get(c.candidate_id) or source
            if not c.candidate_id or item is None:raise ValueError('candidate_id_required')
            if c.name and c.name.casefold()!=item.get('name',item.get('canonical_name','')).casefold():raise ValueError('candidate_name_mismatch')
            if group=='removes':
                if counts.get(c.candidate_id,0)<c.quantity:raise ValueError('cut_exceeds_source')
                counts[c.candidate_id]-=c.quantity
            else:counts[c.candidate_id]=counts.get(c.candidate_id,0)+c.quantity
    return Proposal(kind='list',name=report['name'],cards=tuple(Candidate(candidate_id=key,quantity=n) for key,n in counts.items() if n),rationale=proposal.rationale)


def source_hash(artifact):return digest(artifact['report'])


def change_set(artifact, proposal, report):
    value=dict(type='proposed_change_set',status='PROPOSED',source_artifact_id=artifact['id'],
        source_artifact_hash=source_hash(artifact),proposal=proposal.model_dump(mode='json'),
        reasoning=proposal.rationale,validation_status=report['validation_status'])
    value['id']=digest(value)
    return value


def select(history):
    artifacts=history.get('artifacts',{});source=artifacts.get('generated_deck')
    pending=artifacts.get('proposed_change_set')
    # A future multi-option producer must choose explicitly; never pick silently.
    if isinstance(pending,list):return None,'Which proposed change set should I apply?'
    if not pending or pending.get('status')!='PROPOSED':return None,'Which exact changes should I propose for this generated deck?'
    if not source or pending['source_artifact_id']!=source['id'] or pending['source_artifact_hash']!=source_hash(source):
        return None,'Those changes refer to an older deck. Should I propose changes for the current generated deck?'
    return pending,None


CONTRACT='''
current_generated_deck is the current conversational deck, separate from the saved
active deck. Discussion/critique/explanation requires no action block. For
DISCUSS, its resolved identities, quantities and validation status are authoritative:
do not call it a placeholder or claim its known cards are unavailable. Do not emit
a generated_deck or changes block. candidate_sandbox.consensus records its original
baseline when present; do not invent deviations if the current quantities match.
For
generated_intent RECOMMEND, give a specific rationale and one proposed_deck_changes
block with exact candidate_id and quantity for every remove/add. Choose only the
supplied candidate_sandbox; cuts must exist in current_generated_deck. Balance to
60 and respect construction limits. The server binds the proposal to this artifact;
do not emit a replacement generated_deck for a recommendation. If no useful exact
recommendation is available, explain the constraint without inventing candidates.
Use canonical supplied names. Keep evidence IDs in fact_ids, never visible prose.
Ordinary strategy is conversational; do not append Sources or printed-data dumps.
'''
