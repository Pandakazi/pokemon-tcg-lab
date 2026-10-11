"""Conversation-only generated-deck referents. Never mutate workspace state."""
from copy import deepcopy
import json
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


def compose(artifact, proposal, sandbox=None):
    """Bind functional IDs, reject phantom/excess cuts, retain every other slot."""
    report=artifact['report'];sandbox=sandbox or report.get('candidate_sandbox') or {}
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
        cuts=[dict(candidate_id=c.candidate_id,quantity=c.quantity) for c in proposal.removes],
        adds=[dict(candidate_id=c.candidate_id,quantity=c.quantity) for c in proposal.adds],
        reasoning=proposal.rationale,validation_status=report['validation_status'])
    original=artifact['report'].get('candidate_sandbox',{}).get('candidates',[])
    known={r['candidate_id'] for r in original}
    extra=[deepcopy(r) for r in report.get('candidate_sandbox',{}).get('candidates',[])
        if r['candidate_id'] not in known and r['candidate_id'] in {c.candidate_id for c in proposal.adds}]
    if extra:value['replacement_candidates']=extra
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


def replacement_pool(path, artifact, **kwargs):
    """Fresh role-ranked alternatives, with every current identity retained.

    This changes recommendation context only, never custom generation or consensus.
    The original packet remains immutable and bounded; legal resolution still reads DB.
    """
    from .agent_deck_sandbox import build,MAX_CANDIDATES
    report=artifact['report'];original=report['candidate_sandbox']
    core=[r['name'] for r in original['candidates'] if r.get('requested_core')]
    fresh=build(path,'Recommend support changes for '+', '.join(core),
        [r['printing_id'] for r in report['cards']],**kwargs)
    current={r['candidate_id'] for r in report['cards']}
    rows={r['candidate_id']:deepcopy(r) for r in original['candidates'] if r['candidate_id'] in current}
    # A currently legal identity may have been absent from an older compact packet.
    for r in fresh['candidates']:
        if r['candidate_id'] in current:rows.setdefault(r['candidate_id'],deepcopy(r))
    if set(rows)!=current:raise ValueError('current_candidate_coverage')
    for r in [*fresh['candidates'],*original['candidates']]:
        if len(rows)>=MAX_CANDIDATES:break
        rows.setdefault(r['candidate_id'],deepcopy(r))
    fields=('candidate_id','printing_id','name','category','role','ace_spec','basic_energy',
        'copy_limit_name','requested_core','predecessor_candidate_ids','stage','evolveFrom',
        'types','attacks','abilities','effect','rules')
    fresh_by_id={r['candidate_id']:r for r in fresh['candidates']}
    projected=[]
    for r in rows.values():
        item={k:r[k] for k in fields if k in r}
        item['strategic_roles']=fresh_by_id.get(r['candidate_id'],r).get('ranking',{}).get('roles',r.get('strategic_roles',[]))
        projected.append(item)
    return dict(original,candidates=projected,
        replacement_pool=True)


RECOMMEND_SYSTEM='''Return ONLY one JSON object, before any user explanation:
{"source_artifact_id":"current_generated_deck.id",
 "source_artifact_hash":"current_generated_deck.artifact_hash",
 "cuts":[{"candidate_id":"exact supplied ID","quantity":1}],
 "adds":[{"candidate_id":"exact supplied ID","quantity":1}]}
Use the actual source ID/hash. No prose, card names, rationale, markdown or actions block.
Answer the user's exact-change request using a small useful role-appropriate tradeoff.
Both arrays must be nonempty. Cuts must exist in the current deck and not exceed its
quantities. Adds must use candidate_sandbox IDs. Balance removals and additions to 60.
Group ordinary copies by copy_limit_name for maximum 4, except basic_energy; at most
one ACE SPEC. Preserve the requested core and evolution support. Never invent cards.
If a preferred conceptual card is unavailable, select the next legal role-appropriate
alternative in this sandbox. On retry, revise the failed choices using these candidates.
If no meaningful improvement can be justified, return only
{"source_artifact_id":"actual ID","source_artifact_hash":"actual hash","no_material_improvement":true}.
Do not fabricate a swap just to produce actions.
PokéLab validates first and renders the canonical Cut/Add explanation afterward.
'''


def structured(text, artifact):
    """Strict bound JSON; legacy action blocks are read for wire compatibility only.

    Legacy prose is discarded, never parsed for candidates or shown as changes.
    """
    if len(text.encode())>8192:raise ValueError('change_budget_exceeded')
    if '<POKELAB_ACTIONS>' in text:
        from .agent_hybrid import parse
        _,proposal,issues=parse(text,True)
        if issues or not proposal or proposal.kind!='diff':raise ValueError('change_contract_invalid')
    else:
        value=json.loads(text)
        if not isinstance(value,dict) or set(value)!= {'source_artifact_id','source_artifact_hash','cuts','adds'}:raise ValueError('change_contract_invalid')
        if value['source_artifact_id']!=artifact['id'] or value['source_artifact_hash']!=source_hash(artifact):raise ValueError('change_source_mismatch')
        def entries(group):
            rows=value[group]
            if not isinstance(rows,list) or not 1<=len(rows)<=60:raise ValueError('change_entries_invalid')
            for r in rows:
                if not isinstance(r,dict) or set(r)!={'candidate_id','quantity'}:raise ValueError('change_entries_invalid')
            return tuple(Candidate(**r) for r in rows)
        proposal=Proposal(kind='diff',removes=entries('cuts'),adds=entries('adds'))
    if not proposal.removes or not proposal.adds:raise ValueError('balanced_changes_required')
    for group in (proposal.removes,proposal.adds):
        ids=[r.candidate_id for r in group]
        if not all(ids) or len(set(ids))!=len(ids):raise ValueError('unique_candidate_ids_required')
    if set(c.candidate_id for c in proposal.removes)&set(c.candidate_id for c in proposal.adds):raise ValueError('cancelled_changes')
    if sum(c.quantity for c in proposal.removes)!=sum(c.quantity for c in proposal.adds):raise ValueError('balanced_changes_required')
    return proposal.model_copy(update={'rationale':''})


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
