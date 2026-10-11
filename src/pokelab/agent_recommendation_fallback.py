"""Diagnose exact recommendations before bounded, role-specific recovery.

No generation/ranking/legality changes. Every fallback uses the existing validator.
Diagnostics contain structured selections and safe reason codes, never raw output.
"""
from copy import deepcopy
from collections import Counter
import json
from .agent_generated_changes import structured,compose,source_hash
from .agent_deck_proposals import Proposal,Candidate,evaluate

ADJACENT={'setup-search':('draw-consistency','evolution-support','recovery'),
    'draw-consistency':('setup-search','recovery'), 'evolution-support':('setup-search','draw-consistency'),
    'recovery':('setup-search','energy-support'), 'gust':('disruption','mobility'),
    'disruption':('gust','draw-consistency'), 'mobility':('tool','energy-support'),
    'energy-support':('recovery','draw-consistency'), 'tool':('mobility','draw-consistency'),
    'stadium':('disruption','draw-consistency')}


def roles(row):
    return set(row.get('strategic_roles') or row.get('ranking',{}).get('roles',[]))


def assessment(text,source,envelope,sources,request):
    attempt=dict(source_artifact_id=source['id'],cuts=[],adds=[],failure_reason=None,
        blocked_candidate_ids=[],retry_strategy=None,final_status='REJECTED')
    proposal=None;report=None
    try:
        try:value=json.loads(text)
        except (ValueError,TypeError):value=None
        if isinstance(value,dict):
            for group in ('cuts','adds'):
                rows=value.get(group,[])
                if isinstance(rows,list):attempt[group]=[dict(candidate_id=r['candidate_id'],quantity=r['quantity']) for r in rows[:60] if isinstance(r,dict) and isinstance(r.get('candidate_id'),str) and 0<len(r['candidate_id'])<=100 and type(r.get('quantity')) is int and 0<r['quantity']<=999]
        if isinstance(value,dict) and set(value)=={'source_artifact_id','source_artifact_hash','no_material_improvement'} and value['no_material_improvement'] is True:
            if value['source_artifact_id']!=source['id'] or value['source_artifact_hash']!=source_hash(source):raise ValueError('change_source_mismatch')
            attempt['failure_reason']='no_material_improvement_found';return None,None,attempt
        proposal=structured(text,source)
        for group,field in [('removes','cuts'),('adds','adds')]:
            attempt[field]=[dict(candidate_id=c.candidate_id,quantity=c.quantity) for c in getattr(proposal,group)]
        allowed={r['candidate_id'] for r in envelope['candidate_sandbox']['candidates']}
        outside=[c.candidate_id for c in proposal.adds if c.candidate_id not in allowed]
        if outside:
            required=set(envelope.get('required_replacement_candidate_ids',[]))
            reason='context_budget_trimmed_required_candidates' if set(outside)<=required else 'candidate_outside_sandbox'
            attempt.update(failure_reason=reason,blocked_candidate_ids=outside);return proposal,None,attempt
        report,_,_=evaluate(compose(source,proposal,envelope['candidate_sandbox']),(),sources,request.model_copy(update={'include_deck':False}),envelope)
        violations=report.get('construction_violations',[])
        if any(v['kind']=='name_copy_limit' for v in violations):
            names={v['name'] for v in violations if v['kind']=='name_copy_limit'}
            blocked=[r['candidate_id'] for r in envelope['candidate_sandbox']['candidates'] if r['copy_limit_name'] in names]
            attempt.update(failure_reason='copy_limit_violation',blocked_candidate_ids=blocked)
        elif any(v['kind']=='ace_spec' for v in violations):
            attempt.update(failure_reason='ace_spec_violation',blocked_candidate_ids=[r['candidate_id'] for r in envelope['candidate_sandbox']['candidates'] if r.get('ace_spec')])
        elif report.get('unresolved'):
            attempt.update(failure_reason='legality_violation',blocked_candidate_ids=[r['candidate_id'] for r in report['unresolved'] if r.get('candidate_id')])
        elif report['validation_status']=='STALE':attempt['failure_reason']='stale_source_artifact'
        elif report['total_cards']!=60:attempt['failure_reason']='no_valid_balanced_swap'
        elif report['validation_status']!='VALIDATED':attempt['failure_reason']='unknown_validation_failure'
        else:attempt['final_status']='VALIDATED'
    except (ValueError,TypeError,KeyError) as exc:
        attempt['failure_reason']={'change_source_mismatch':'stale_source_artifact',
            'cut_exceeds_source':'no_valid_balanced_swap','balanced_changes_required':'no_valid_balanced_swap',
            'cancelled_changes':'no_valid_balanced_swap'}.get(str(exc),'proposal_contract_invalid')
    return proposal,report,attempt


def expand(source,envelope,sources,wanted):
    """Admit up to eight alternatives using existing legal pool and role ranking."""
    from .agent_deck_sandbox import legal_pool,retrieval,MAX_CANDIDATES,FIELDS
    from .agent_candidate_quality import rank
    from .engine import normalized_name
    pool=legal_pool(sources.paths['cards']);byid={r['functional_id']:r for r in pool}
    core=[byid[r['candidate_id']] for r in envelope['candidate_sandbox']['candidates'] if r.get('requested_core') and r['candidate_id'] in byid]
    ranked=rank(pool,retrieval(pool),core,{},{});current={r['candidate_id'] for r in source['report']['cards']}
    candidates=envelope['candidate_sandbox']['candidates']
    outside_roles=set().union(*(set(ranked[key]['roles']) for key in wanted if key in ranked)) if wanted else set()
    desired=outside_roles or {'setup-search','draw-consistency'}
    adjacent=set().union(*(set(ADJACENT.get(r,())) for r in desired))
    counts=Counter()
    for r in source['report']['cards']:counts[normalized_name(r['canonical_name'])]+=r['quantity']
    choices=sorted((r for r in pool if r['card']['category']=='Trainer' and counts[normalized_name(r['card']['name'])]<4 and set(ranked[r['functional_id']]['roles'])&(desired|adjacent)),key=lambda r:(not bool(set(ranked[r['functional_id']]['roles'])&desired),-ranked[r['functional_id']]['score'],r['functional_id']))
    required=[r for r in candidates if r['candidate_id'] in current];selected={r['candidate_id']:r for r in required}
    for r in choices[:8]:
        key=r['functional_id'];raw=r['card']
        selected.setdefault(key,dict(candidate_id=key,printing_id=r['printing_id'],role='targeted-replacement',
            strategic_roles=ranked[key]['roles'],ace_spec='ACE SPEC' in raw.get('rarity','').upper(),
            basic_energy=False,copy_limit_name=normalized_name(raw['name']),requested_core=False,
            **{k:raw[k] for k in FIELDS if k in raw}))
    for r in candidates:
        if len(selected)>=MAX_CANDIDATES:break
        selected.setdefault(r['candidate_id'],r)
    return dict(envelope['candidate_sandbox'],candidates=list(selected.values())),desired


def retry_context(source,envelope,sources,attempt,proposal):
    retry=deepcopy(envelope);reason=attempt['failure_reason'];blocked=set(attempt['blocked_candidate_ids'])
    if reason=='proposal_contract_invalid':strategy='repair_structured_contract'
    elif reason=='stale_source_artifact':strategy='refresh_source_binding'
    elif reason=='context_budget_trimmed_required_candidates':
        current={r['candidate_id'] for r in retry['candidate_sandbox']['candidates']}
        restored=[r for r in source['report']['candidate_sandbox']['candidates'] if r['candidate_id'] in blocked-current]
        retry['candidate_sandbox']['candidates']+=deepcopy(restored)
        blocked-={r['candidate_id'] for r in restored};strategy='restore_required_candidates'
    elif reason in ('candidate_outside_sandbox','candidate_pool_too_narrow','no_role_match'):
        retry['candidate_sandbox'],desired=expand(source,retry,sources,blocked);strategy='retrieve_same_and_adjacent_roles'
    elif reason=='copy_limit_violation':
        retry['candidate_sandbox'],_=expand(source,retry,sources,blocked);strategy='retrieve_alternatives_below_copy_limit'
    elif reason=='ace_spec_violation':
        retry['candidate_sandbox'],_=expand(source,retry,sources,blocked);strategy='exclude_ace_spec_additions'
    elif reason=='legality_violation':strategy='exclude_unresolved_additions'
    else:strategy='safe_current_consistency_options'
    retry['current_generated_deck'].update(id=source['id'],artifact_hash=source_hash(source))
    candidates=retry['candidate_sandbox']['candidates'];counts=Counter()
    names={r['candidate_id']:r['copy_limit_name'] for r in candidates}
    for r in source['report']['cards']:counts[names.get(r['candidate_id'],r['canonical_name'].casefold())]+=r['quantity']
    available=[]
    for r in candidates:
        if r['candidate_id'] in blocked:continue
        if reason=='ace_spec_violation' and r.get('ace_spec'):continue
        if not r.get('basic_energy') and counts[r['copy_limit_name']]>=4:continue
        if r.get('ace_spec') and any(c.get('ace_spec') and counts[c['copy_limit_name']] for c in candidates):continue
        available.append(r['candidate_id'])
    attempt['retry_strategy']=strategy
    retry['recommendation_retry']=dict(attempt=1,strategy=strategy,reason=reason,blocked_add_candidate_ids=sorted(blocked),
        eligible_add_candidate_ids=available,source_artifact_id=source['id'],source_artifact_hash=source_hash(source))
    # Retry is a compact new transaction. Required IDs survive existing budget fit.
    from .agent_context_budget import fit
    retry=fit(retry,23000)
    from .rules.models import digest
    retry['content_hash']=digest({k:v for k,v in retry.items() if k!='content_hash'})
    return retry


def local_options(source,envelope,sources,request,proposal):
    """Validate same/adjacent-role alternatives to the model's attempted tradeoff.

    No arbitrary 'upgrade': absent a usable strategic direction, only a missing
    search/draw role can justify a conservative current-Trainer ratio adjustment.
    """
    rows=envelope['candidate_sandbox']['candidates'];byid={r['candidate_id']:r for r in rows}
    current={r['candidate_id']:r['quantity'] for r in source['report']['cards']}
    cuts=proposal.removes if proposal else ()
    desired=set().union(*(roles(byid.get(c.candidate_id,{})) for c in proposal.adds)) if proposal else set()
    core={r['candidate_id'] for r in rows if r.get('requested_core')}
    if not cuts or not desired:
        supplied=set().union(*(roles(r) for r in rows if current.get(r['candidate_id'])))
        missing={'setup-search','draw-consistency'}-supplied
        if not missing:return []
        redundant=[r for r in rows if r['category']=='Trainer' and not r.get('ace_spec') and r['candidate_id'] not in core and current.get(r['candidate_id'],0)>=3 and not roles(r)&{'setup-search','draw-consistency','evolution-support'}]
        if not redundant:return []
        cuts=(Candidate(candidate_id=redundant[0]['candidate_id'],quantity=1),);desired=missing
    if any(c.candidate_id in core or current.get(c.candidate_id,0)<c.quantity or byid.get(c.candidate_id,{}).get('category')!='Trainer' for c in cuts):return []
    adjacent=set().union(*(set(ADJACENT.get(r,())) for r in desired));quantity=sum(c.quantity for c in cuts)
    cutids={c.candidate_id for c in cuts};options=[]
    for role_set,strategy in ((desired,'legal_same_role_replacement'),(adjacent,'legal_adjacent_role_replacement')):
        for row in rows:
            if row['candidate_id'] in cutids or row['category']!='Trainer' or not roles(row)&role_set:continue
            p=Proposal(kind='diff',removes=cuts,adds=(Candidate(candidate_id=row['candidate_id'],quantity=quantity),))
            try:
                report,_,_=evaluate(compose(source,p,envelope['candidate_sandbox']),(),sources,request.model_copy(update={'include_deck':False}),envelope)
                if report['validation_status']=='VALIDATED' and report['total_cards']==60:options.append((p,report,strategy))
            except (ValueError,TypeError,KeyError):continue
            if len(options)>=4:return options
    return options


def ratio_option(source,envelope,sources,request):
    """Last resort: redistribute current legal Trainers into a thin support role."""
    rows=envelope['candidate_sandbox']['candidates'];current={r['candidate_id']:r['quantity'] for r in source['report']['cards']}
    support={'setup-search','draw-consistency'};counts=Counter()
    for r in rows:
        for role in roles(r)&support:counts[role]+=current.get(r['candidate_id'],0)
    adds=[r for r in rows if r['category']=='Trainer' and not r.get('ace_spec') and 0<current.get(r['candidate_id'],0)<4 and any(counts[role]<2 for role in roles(r)&support)]
    cuts=[r for r in rows if r['category']=='Trainer' and not r.get('ace_spec') and not r.get('requested_core') and current.get(r['candidate_id'],0)>=3 and not roles(r)&(support|{'evolution-support'})]
    for add in adds[:2]:
        for cut in cuts[:2]:
            proposal=Proposal(kind='diff',removes=(Candidate(candidate_id=cut['candidate_id'],quantity=1),),adds=(Candidate(candidate_id=add['candidate_id'],quantity=1),))
            try:
                report,_,_=evaluate(compose(source,proposal,envelope['candidate_sandbox']),(),sources,request.model_copy(update={'include_deck':False}),envelope)
                if report['validation_status']=='VALIDATED' and report['total_cards']==60:return proposal,report,'safe_current_consistency_adjustment'
            except (ValueError,TypeError,KeyError):continue
    return None


def failure_message(reason):
    return {
        'copy_limit_violation':'The preferred replacements exceed their copy limits, and the remaining legal options did not produce a meaningful balanced swap.',
        'ace_spec_violation':'The proposed changes would exceed the one ACE SPEC limit; no suitable balanced alternative was found.',
        'candidate_outside_sandbox':'The proposed replacement was outside the available legal candidates, and the role-based alternatives did not yield a meaningful upgrade.',
        'legality_violation':'The proposed replacement could not be established as legal; no suitable legal alternative was found.',
        'stale_source_artifact':'The recommendation did not match the current deck even after refreshing its source binding.',
        'proposal_contract_invalid':'The Agent could not return a usable structured change set after a format repair.',
        'no_material_improvement_found':'I couldn’t find a meaningful legal upgrade without changing the deck’s core plan.',
        'no_valid_balanced_swap':'The proposed tradeoff did not yield a valid balanced 60-card list, and no meaningful safe adjustment was found.',
    }.get(reason,'The proposed changes did not pass the current deck checks, and I could not establish a meaningful legal alternative.')+' The current deck is unchanged.'
