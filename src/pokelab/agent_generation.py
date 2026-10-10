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
    custom=custom_request(request.question,c['label'] if c else '')
    # Unspecified builds remain an explicitly labeled custom build. Named generic
    # builds never silently fall through to model invention when data is absent.
    unspecified=not (set(words(request.question))-PRESENTATION_WORDS)
    if custom or unspecified:
        envelope['generation']=dict(generation_source='model_custom',consensus_status=c['status'] if c else 'unavailable',fallback_reason='explicit_constraint' if custom else 'no_archetype_requested')
        envelope['content_hash']=digest({k:v for k,v in envelope.items() if k!='content_hash'})
        return None
    status=c['status'] if c else 'unknown_archetype'
    report=None
    if status=='available':
        from .agent_deck_proposals import evaluate
        from .agent_context_sources import Sources
        report,extra,_=evaluate(proposal_for(c),(),Sources(**service.paths,format_start=service.format_start),request,envelope)
        if report['validation_status']=='VALIDATED':
            generation=dict(generation_source='recent_consensus',consensus_status='complete',fallback_reason=None)
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
    generation=dict(generation_source=None,consensus_status=status,fallback_reason=status)
    envelope['generation']=generation
    artifacts=deepcopy(history.get('artifacts',{}));artifacts['generation_attempt']=generation
    message={'unknown_archetype':'No usable cached Limitless variant matches this request.',
        'insufficient_sample':'There are fewer than eight usable cached lists for this archetype.',
        'allocation_unavailable':'The recent sample could not produce a coherent consensus list.',
        'candidate_budget_unavailable':'The complete consensus exceeds the current candidate budget.',
        'invalid':'The consensus did not pass current validation.'}.get(status,'Recent consensus data is unavailable.')
    answer=dict(version='pokelab-conversation-answer-v1',paragraphs=[dict(text=message+' I have not substituted a model-generated deck. Any existing conversational deck is unchanged.',evidence=[])],facts=[],notices=[],generation=generation)
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
