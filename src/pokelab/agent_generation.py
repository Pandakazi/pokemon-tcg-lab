"""Consensus commit boundary and local explanations; no provider or store writes."""
from copy import deepcopy
import re
from .rules.models import digest
from .agent_consensus import build_request,custom_request,words,PRESENTATION_WORDS,proposal_for
from .agent_artifacts import remember,recount


def finish(service,request,history,envelope,answer,artifacts):
    from .agent_research import canonical
    from .agent_providers import secret_present
    envelope['content_hash']=digest({k:v for k,v in envelope.items() if k!='content_hash'})
    if secret_present(canonical(answer)+canonical(envelope)):return dict(status='secret_input_rejected',answer=None)
    turns=history['turns']+[dict(question=request.question,answer=answer,snapshot=envelope['content_hash'])]
    key=service.conversations.put(request.conversation_id,turns,history['printings'],history.get('proposal'),artifacts)
    return dict(status='answered',answer=answer,envelope=envelope,conversation_id=key,execution=dict(mode='local_artifact',provider_called=False))


def direct_generation(service,request,history,envelope):
    if not build_request(request.question) or envelope['lifecycle']!='FINALIZE' or not envelope.get('artifact_mutation_allowed',True):return None
    c=envelope.get('candidate_sandbox',{}).get('consensus')
    resolution=envelope.get('candidate_sandbox',{}).get('core_resolution',{})
    if resolution.get('status')=='ambiguous':
        choices=resolution['choices']
        generation=dict(generation_source=None,consensus_status='unavailable',failure_reason='ambiguous_legal_core')
        envelope['generation']=generation
        answer=dict(version='pokelab-conversation-answer-v1',paragraphs=[dict(text='Do you want '+' or '.join(r['label'] for r in choices)+'?',evidence=[])],facts=[],notices=[],generation=generation)
        artifacts=deepcopy(history.get('artifacts',{}))
        artifacts.pop('selected_core',None)
        from .agent_build_core import theme as core_theme
        artifacts['pending_build']=dict(question=request.question,choices=choices,format='standard',source_turn=history.get('turn_number',0)+1,status='awaiting_core',theme=core_theme(choices[0]['canonical_name']))
        artifacts['build_clarification']=dict(question=request.question,choices=choices)
        return finish(service,request,history,envelope,answer,artifacts)
    if resolution.get('reason')=='selected_core_not_standard_legal':return failed_build(service,request,history,envelope,'unresolved_core')
    core=[r for r in envelope.get('candidate_sandbox',{}).get('candidates',[]) if r.get('requested_core') and r.get('category')=='Pokemon']
    themes={}
    for r in core:
        theme=re.sub(r'^mega\s+|\s+ex$', '',r['name'].casefold())
        themes.setdefault(theme,[]).append(r)
    custom=custom_request(request.question,c['label'] if c else '')
    # Explicit constraints and unspecified builds retain the existing custom path.
    unspecified=not (set(words(request.question))-PRESENTATION_WORDS)
    if custom or unspecified:
        # A theme-only novice request is not an arbitrary strategic constraint.
        style=bool(re.search(r'\b(?:aggressive|control|experimental|custom|weird|budget|mill|stall|toolbox)\b',request.question,re.I))
        if c or unspecified or style or len(themes)>1:return custom_generation(envelope,c,'explicit_constraint' if custom else 'no_archetype_requested')
    status=c['status'] if c else 'unknown_archetype'
    # A species-level cached shell cannot silently replace a user-selected
    # gameplay core. Its sampling/allocation is untouched; use custom fallback.
    selected=envelope.get('selected_core')
    if status=='available' and selected and selected['candidate_id'] not in {r['candidate_id'] for r in c['cards']}:
        return custom_generation(envelope,c,'selected_core_not_in_consensus',core)
    report=None
    if status=='available':
        from .agent_deck_proposals import evaluate
        from .agent_context_sources import Sources
        report,extra,_=evaluate(proposal_for(c),(),Sources(**service.paths,format_start=service.format_start),request,envelope,consensus_ids=[r['candidate_id'] for r in c['cards']])
        if report['validation_status']=='VALIDATED':
            explicit=c.get('explicit_variant') or (len(words(c['label']))>1 and not c['label'].casefold().startswith('mega ') and set(words(c['label']))<=set(words(request.question)))
            generation=dict(build_mode='consensus',generation_source='recent_consensus_explicit_variant' if explicit else 'recent_consensus',consensus_status='complete',fallback_reason=None)
            report.update(generation);envelope['generation']=generation
            # Compact provenance stays inspectable, but does not open evidence by default.
            envelope['evidence'].append(dict(id='recent-consensus',kind='evidence',title='Recent archetype consensus',value={k:c[k] for k in ('label','event_ids','sample_size','placement_band','placement_weights','shape','energy')},source=c['source']))
            envelope['content_hash']=digest({k:v for k,v in envelope.items() if k!='content_hash'})
            artifacts=remember(history,report,envelope)
            if report['validation_status']=='VALIDATED' and artifacts.get('generated_deck'):
                answer=recount(dict(artifacts=artifacts),'generated_deck');answer['historical_snapshot']=False
                answer['paragraphs']=[dict(text='This is the recent competitive consensus baseline. No model substitutions were made; you can ask me to explain it or propose changes.',evidence=[])]
                answer['completion']=dict(status='complete',repair_attempts=0)
                return finish(service,request,history,envelope,answer,artifacts)
        status='invalid'
    if core:
        return custom_generation(envelope,c,status,core)
    if resolution.get('status')=='selected':return failed_build(service,request,history,envelope,'candidate_budget_insufficient')
    generation=dict(generation_source=None,consensus_status=status,fallback_reason=status,failure_reason='requested_core_unresolved_or_not_standard_legal')
    envelope['generation']=generation
    artifacts=deepcopy(history.get('artifacts',{}));artifacts['generation_attempt']=generation
    message={'unknown_archetype':'No usable cached Limitless variant matches this request.',
        'insufficient_sample':'There are fewer than eight usable cached lists for this archetype.',
        'allocation_unavailable':'The recent sample could not produce a coherent consensus list.',
        'candidate_budget_unavailable':'The complete consensus exceeds the current candidate budget.',
        'invalid':'The consensus did not pass current validation.'}.get(status,'Recent consensus data is unavailable.')
    answer=dict(version='pokelab-conversation-answer-v1',paragraphs=[dict(text=message+' I have not substituted a model-generated deck. Any existing conversational deck is unchanged.',evidence=[])],facts=[],notices=[],generation=generation)
    return finish(service,request,history,envelope,answer,artifacts)


def custom_generation(envelope,consensus,reason,core=()):
    from .agent_custom_build import shape
    envelope['custom_shape_prior']=shape(envelope['candidate_sandbox'])
    envelope['generation']=dict(build_mode='custom',generation_source='custom_model_build',
        consensus_status='no_matching_variant' if consensus is None else 'unavailable',
        fallback_reason=reason,requested_core_ids=[envelope['selected_core']['candidate_id']] if envelope.get('new_build') and envelope.get('selected_core') else [r['candidate_id'] for r in core])
    envelope['generation_instruction']='This is a CUSTOM Standard build, not an established tournament consensus. Preserve the requested legal core. Use the supplied candidate_id sandbox and construction constraints; label strategic choices as judgment. Do not claim a recent tournament shell or consensus without supplied evidence.'
    envelope['content_hash']=digest({k:v for k,v in envelope.items() if k!='content_hash'})
    return None


def failed_build(service,request,history,envelope,reason):
    if reason=='unresolved_core' and envelope.get('selected_core'):
        envelope['selected_core']=dict(envelope['selected_core'],status='UNAVAILABLE')
    generation=envelope.get('generation') or dict(build_mode='custom',generation_source=None,consensus_status='unavailable')
    generation=dict(generation,failure_reason=reason)
    envelope['generation']=generation
    answer=dict(version='pokelab-conversation-answer-v1',paragraphs=[dict(text='I could not complete this custom Standard build: '+reason.replace('_',' ')+'. No completed deck is claimed; any existing conversational deck is unchanged.',evidence=[])],facts=[],notices=[],generation=generation,build_failure=dict(reason=reason),completion=dict(status='incomplete',repair_attempts=0,reason=reason))
    artifacts=remember(history,None,envelope);artifacts['generation_attempt']=generation
    return finish(service,request,history,envelope,answer,artifacts)


def unchanged_consensus(service,request,history,envelope):
    if not re.search(r'\bdeviat\w*\b',request.question,re.I):return None
    artifact=history.get('artifacts',{}).get('generated_deck',{});report=artifact.get('report',{})
    c=report.get('candidate_sandbox',{}).get('consensus')
    if not c or c['status']!='available':return None
    current={r.get('candidate_id'):r['quantity'] for r in report['cards']}
    baseline={r['candidate_id']:r['quantity'] for r in c['cards']}
    if current!=baseline:return None
    answer=dict(version='pokelab-conversation-answer-v1',paragraphs=[dict(text='I did not make a model-driven deviation: the current list equals the recent consensus baseline. Fractional source averages were allocated into a coherent 60-card list.',evidence=[])],facts=[],notices=[])
    return finish(service,request,history,envelope,answer,deepcopy(history.get('artifacts',{})))
