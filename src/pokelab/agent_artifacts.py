"""Bounded conversation artifacts and a single presentation boundary. No writes."""
from copy import deepcopy
import json
import re
from .rules.models import digest


def artifact_context(history):
    return {kind:dict(id=a['id'],source_turn=a['source_turn'],report={k:a['report'].get(k) for k in ('name','cards','adds','removes','unresolved','category_subtotals','total_cards','validation_status','hard_validation')}) for kind,a in history.get('artifacts',{}).items() if isinstance(a,dict) and 'report' in a}


def remember(history, report, envelope):
    artifacts=deepcopy(history.get('artifacts',{}))
    if report and report['kind'] in ('list','diff'):
        kind='generated_deck' if report['kind']=='list' else 'proposed_deck_changes'
        # Keep resolved identities/counts/status independent of compacted prose.
        saved=deepcopy(report)
        for group in ('cards','adds','removes'):
            saved[group]=[{k:v for k,v in r.items() if k not in ('printed','checked_at','source','content_hash')} for r in saved[group]]
        saved['alternatives']=[]
        turn=history.get('turn_number',0)+1
        item=dict(type=kind,pending=report['validation_status']!='VALIDATED',source_turn=turn,source_snapshot=envelope['content_hash'],report=saved)
        item['id']=digest(item)
        if len(json.dumps(item).encode())<=65536:
            artifacts[kind]=item
            if kind=='generated_deck':artifacts.pop('deck_referent',None)
        else:
            artifacts.pop(kind,None)
            report['validation_status']='NEEDS_REPAIR'
            report['hard_validation'].append('This artifact exceeds the conversation storage budget and cannot be retained for recount. It is not a finalized deck.')
    return artifacts


def recount_target(question):
    # Intent dispatch only: never derive entries or counts from natural prose.
    q=question.casefold()
    if not re.search(r'recount|show.*(?:again|list)|what exact cards|how many cards|what.*cards.*(?:were|in the.*proposed)',q):return None
    if re.search(r'add|cut|remove|replace|change.*(?:to|with)',q):return None
    return 'proposed_deck_changes' if re.search(r'that change|proposed changes|that diff',q) else 'generated_deck'


def recount(history,target):
    artifact=history.get('artifacts',{}).get(target)
    if not artifact:return None
    report=deepcopy(artifact['report'])
    report['total_cards']=sum(r['quantity'] for r in report['cards'])
    report['category_subtotals']={category:sum(r['quantity'] for r in report['cards'] if r['category']==category) for category in ('Pokemon','Trainer','Energy')}
    return dict(version='pokelab-conversation-answer-v1',paragraphs=[],facts=[],proposal=report,
        artifact_id=artifact['id'],source_turn=artifact['source_turn'],historical_snapshot=True,notices=[])


def present(prose,parsed,report,rejected,issues,envelope,sources,request):
    """Keep original safe sentences; withhold whole unsafe units, never splice text.

    Printed factual clauses become typed review data and local evidence. Provider
    arithmetic is never used for artifacts, totals, or validation.
    """
    from .agent_conversation import EMPIRICAL,unsupported_identity
    from .agent_deck_proposals import quantity_claim
    from .agent_card_facts import review
    from .agent_research import ContractError
    answer=dict(version='pokelab-conversation-answer-v1',paragraphs=[],facts=[],notices=[],fact_reviews=[])
    resolution=report if report and report['kind']=='list' else envelope.get('artifacts',{}).get('generated_deck',{}).get('report',{})
    envelope['resolution_artifact']={key:resolution.get(key,[]) for key in ('cards','unresolved')}
    unresolved={r['name'].casefold() for r in resolution.get('unresolved',[]) if r.get('name')}
    envelope['evidence']=[e for e in envelope['evidence'] if not e.get('printing') or e['title'].casefold() not in unresolved]
    qualified=False;known={e['id'] for e in envelope['evidence']};fact_ids=set(parsed.fact_ids)&known
    concrete=bool(report and report['kind'] in ('list','diff')) or envelope['lifecycle'] in ('RECOMMEND','FINALIZE')
    texts=[prose]
    if parsed.proposal and parsed.proposal.rationale and parsed.proposal.rationale not in prose:texts.append(parsed.proposal.rationale)
    for text in texts:
        text=clean_references(text,envelope)
        if not text.strip():continue
        invalid_dependency=False
        for unit in re.split(r'(?<=[.!?])\s+|\n+',text):
            unit=unit.strip()
            if not unit or not re.search(r'\w',unit):continue
            if any(name and name.casefold() in unit.casefold() for name in rejected):
                invalid_dependency=True;continue
            if invalid_dependency and re.match(r'(?:It|This|That|Doing so|They)\b',unit,re.I):continue
            invalid_dependency=False
            if EMPIRICAL.search(unit):qualified=True;continue
            reviews,facts=review(unit,sources,request,envelope)
            if reviews:
                answer['fact_reviews'].extend(reviews)
                for fact in facts:
                    fact_ids.add(fact['id'])
                    if fact['id'] not in known:envelope['evidence'].append(fact);known.add(fact['id'])
                continue
            if unsupported_identity(unit,envelope):
                answer['fact_reviews'].append(dict(status='unresolved',references=[]));continue
            if concrete and (quantity_claim(unit) or re.search(r'\b(?:legal|illegal|validated|complete|finished|deck size|copy limit|contains|deck has|deck includes)\b',unit,re.I)):
                continue
            # Retain annotations only for unchanged legacy paragraphs.
            refs=next((p.evidence for p in parsed.paragraphs if p.text==unit),())
            answer['paragraphs'].append(dict(text=unit,evidence=[ref for ref in refs if ref in known][:12]))
    if report:
        answer['proposal']=report
        if issues:
            report.update(validation_status='NEEDS_REPAIR',resolution_status='UNRESOLVED',legality_status='UNKNOWN')
            report['hard_validation'].append('The structured artifact is incomplete; review unresolved entries.')
    elif envelope['lifecycle'] in ('RECOMMEND','FINALIZE') and not envelope.get('generated_intent'):
        answer['notices'].append('missing_artifact')
    if issues:answer['action_diagnostics']=issues
    if qualified:answer['notices'].append('empirical_claim_unverified')
    if answer['fact_reviews'] and (not envelope.get('generated_intent') or any(r['status']!='printed_reference' for r in answer['fact_reviews'])):answer['notices'].append('printed_fact_review')
    answer['facts']=[e for e in envelope['evidence'] if e['id'] in fact_ids]
    if not prose.strip() and not report:raise ContractError('empty_statement')
    envelope['content_hash']=digest({k:v for k,v in envelope.items() if k!='content_hash'})
    return answer,qualified


def clean_references(text,envelope):
    """Render identity-bound labels canonically; don't guess unannotated aliases."""
    names={e['id']:e['title'] for e in envelope['evidence'] if e.get('printing')}
    for row in envelope.get('current_generated_deck',{}).get('cards',[]):
        names[row['candidate_id']]=row['canonical_name']
    def label(match):
        canonical=names.get(match['id'])
        if not canonical:return match['label']
        words=match['label'].split();prefix=words[:-len(canonical.split())]
        return ' '.join([*prefix,canonical])
    text=re.sub(r"(?P<label>[A-Z][\w’'-]*(?: (?:[A-Z][\w’'-]*|ex)){0,3})\s*\[(?P<id>card-[^\]\s]+)\]",label,text)
    text=re.sub(r'\[(?:card-[^\]]*|fact_ids\s*:[^\]]*)\]','',text)
    return re.sub(r' +([.,;!?])',r'\1',re.sub(r' {2,}',' ',text)).strip()


def pending_repair(question, history):
    """A small confirmation dispatcher, gated by an actual unresolved artifact."""
    artifact=history.get('artifacts',{}).get('generated_deck')
    if not artifact or not artifact.get('pending'):return None
    words=set(re.findall(r"[a-z]+",question.casefold()))
    if words & {'why','explain','not','dont','don','never','cancel','instead','new','different'}:return None
    action=bool(words & {'finish','fix','complete','fill','resolve','repair'}) or ('make' in words and 'legal' in words)
    confirmation=bool(words & {'do','proceed','yes','okay','ok','sure'}) and not (words & {'think','what','how'})
    reference='60' in question or bool(words & {'it','that','those','list','deck','rest','slots','them'}) or words<= {'yes','okay','ok','sure','please','proceed'}
    return artifact if reference and (action or confirmation) else None


def repair_requirements(report):
    """Compact local failures and legal candidates, never chosen replacement slots."""
    if not report:return dict(format='standard',target_total=60,failures=['A generated_deck artifact is required.'])
    from .agent_deck_sandbox import accounting
    from .agent_deck_completion import eligible
    return dict(mode='additive_completion' if eligible(report) else 'replacement',required_delta=accounting(report)['true_missing_count'] if eligible(report) else None,format='standard',target_total=60,name=report['name'],accounting=accounting(report),
        missing_copies=accounting(report)['true_missing_count'],construction_violations=report.get('construction_violations',[]),candidate_sandbox=report.get('candidate_sandbox'),
        cards=[{k:r.get(k) for k in ('candidate_id','canonical_name','printing_id','quantity','category')} for r in report['cards']],
        total=report['total_cards'],unresolved=report['unresolved'],
        failures=report['hard_validation'][:12],
        alternatives=[dict(for_card=g.get('for_card'),role=g.get('role'),candidates=[{k:r.get(k) for k in ('canonical_name','printing_id','tier','printed')} for r in g.get('candidates',[]) if r.get('standard') is True][:3]) for g in report['alternatives'][:8]])
