"""Small gameplay-level build-around defaults; no printing/legality/ranking rewrites."""
import re
from .engine import normalized_name


def theme(name):return re.sub(r'^mega\s+|\s+ex$', '',normalized_name(name))


def strength(row):
    """A transparent novice default, not a competitive/card-quality verdict."""
    card=row['card'];name=normalized_name(card['name'])
    box=name.endswith(' ex') or bool(card.get('suffix')) or any('rule' in str(r).casefold() for r in card.get('rules',[]))
    def number(value):
        match=re.match(r'^\d+',str(value or ''))
        return int(match[0]) if match else 0
    damage=max((number(a.get('damage')) for a in card.get('attacks',[])),default=0)
    return (100 if box else 0)+(20 if name.startswith('mega ') else 0)+min(30,damage//10)+min(8,number(card.get('hp'))//50)


def label(row, peers):
    name=row['card']['name']
    if sum(normalized_name(r['card']['name'])==normalized_name(name) for r in peers)==1:return name
    def names(r):return [x.get('name','') for key in ('abilities','attacks') for x in r['card'].get(key,[])]
    components=names(row)
    # Describe the gameplay choice, never the collector/printing identifier.
    detail=' / '.join(x for x in components if x)
    if sum(normalized_name(r['card']['name'])==normalized_name(name) and names(r)==components for r in peers)>1:
        card=row['card'];parts=[str(card.get('hp',''))+' HP'] if card.get('hp') else []
        for key in ('abilities','attacks'):
            for x in card.get(key,[]):
                values=[x.get('name',''),str(x.get('damage','')), '/'.join(x.get('cost',[])),x.get('effect','')]
                parts.append(' · '.join(v for v in values if v))
        detail='; '.join(parts)
    return name+' — '+(detail[:240] or 'different printed effect')


def resolve(pool,question,consensus=None,selected_core=None):
    q=normalized_name(question)
    def mentioned(row):
        name=normalized_name(row['card']['name'])
        return bool(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',q) or
            (row['card']['category']=='Pokemon' and re.search(r'(?<!\w)'+re.escape(theme(name))+r'(?!\w)',q)))
    core=[r for r in pool if mentioned(r)]
    pokemon=[r for r in core if r['card']['category']=='Pokemon']
    groups={theme(r['card']['name']) for r in pokemon}
    if selected_core:
        chosen=next((r for r in pool if r['functional_id']==selected_core['candidate_id']),None)
        if not chosen:return [],dict(status='unresolved',reason='selected_core_not_standard_legal')
        core=[r for r in core if theme(r['card']['name'])!=theme(chosen['card']['name'])]
        core.append(chosen)
        return core,selection(chosen,selected_core.get('selection_source','user_selected'))
    if len(groups)!=1:return core,dict(status='multiple_requested' if pokemon else 'unresolved')
    # Explicit ex/Mega or regular/baby requests constrain this choice, never
    # silently favor an exact-name baby in an otherwise generic species request.
    explicit=[r for r in pokemon if (normalized_name(r['card']['name']).startswith('mega ') or normalized_name(r['card']['name']).endswith(' ex'))
        and re.search(r'(?<!\w)'+re.escape(normalized_name(r['card']['name']))+r'(?!\w)',q)]
    regular=bool(re.search(r'\b(?:regular|baby|non.ex)\b',q))
    if regular:pokemon=[r for r in pokemon if not normalized_name(r['card']['name']).endswith(' ex') and not r['card'].get('suffix')]
    elif explicit:
        longest=max(len(r['card']['name']) for r in explicit)
        pokemon=[r for r in explicit if len(r['card']['name'])==longest]
    if not pokemon:return [],dict(status='unresolved',reason='requested_core_unresolved_or_not_standard_legal')
    # The certified index already supplies one row per gameplay identity. Never
    # infer equivalence by name or merge different printed effects here.
    pokemon=list({r['functional_id']:r for r in pokemon}.values())
    quantities={r['candidate_id']:r['quantity'] for r in (consensus or {}).get('cards',[])} if (consensus or {}).get('status')=='available' else {}
    observed=[r for r in pokemon if r['functional_id'] in quantities]
    source='user_selected' if explicit or regular else 'auto_buildaround'
    if observed:
        chosen=max(observed,key=lambda r:(strength(r),quantities[r['functional_id']],r['functional_id']))
        source='recent_consensus'
    else:
        ordered=sorted(pokemon,key=lambda r:(-strength(r),r['functional_id']))
        if len(ordered)>1 and strength(ordered[0])-strength(ordered[1])<=10:
            plausible=[r for r in ordered if strength(ordered[0])-strength(r)<=10]
            return core,dict(status='ambiguous',choices=[dict(candidate_id=r['functional_id'],canonical_name=r['card']['name'],label=label(r,plausible)) for r in plausible[:4]])
        chosen=ordered[0]
    return [r for r in core if r['card']['category']!='Pokemon']+[chosen],selection(chosen,source)


def selection(row,source):
    return dict(status='selected',selected_core=dict(candidate_id=row['functional_id'],canonical_name=row['card']['name'],format='standard',selection_source=source,status='RESOLVED'))


def prepare(request,history):
    """Resolve a gameplay choice/referent from bounded structured state."""
    artifacts=history.get('artifacts',{});pending=artifacts.get('build_clarification')
    q=normalized_name(request.question).rstrip('.!?')
    if pending:
        choices=pending.get('choices',[])
        matches=[r for r in choices if q in (normalized_name(r['canonical_name']),normalized_name(r['label']))]
        if len(matches)==1:
            row=matches[0]
            core=dict(candidate_id=row['candidate_id'],canonical_name=row['canonical_name'],format='standard',selection_source='user_selected',status='RESOLVED')
            return request.model_copy(update={'question':pending['question']+' Selected build-around: '+row['canonical_name']+'.'}),core
    core=artifacts.get('selected_core')
    if core and re.fullmatch(r'(?:please )?(?:build (?:me )?(?:a )?(?:deck )?around (?:it|that card)|(?:build|make) (?:me )?(?:a )?deck (?:around|with) (?:it|that|that card)|use that one)',q):
        return request.model_copy(update={'question':'Build me a Standard deck around '+core['canonical_name']+'.'}),core
    return request,None
