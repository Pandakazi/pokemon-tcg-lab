"""Small gameplay-level build-around defaults; no printing/legality/ranking rewrites."""
import re
import json
from copy import deepcopy
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
    return (100 if box else 0)+(20 if name.startswith('mega ') else 0)+(12 if card.get('abilities') else 0)+min(30,damage//10)+min(8,number(card.get('hp'))//50)


def choice_signature(card):
    """Selection-only comparison; never rewrite persisted functional identities.

    Collapse redundant ex suffix metadata and multiplier glyph spelling only.
    All other indexed gameplay fields and construction classes remain compared.
    """
    from .functional_index import gameplay_signature
    value=json.loads(gameplay_signature(card))
    if normalized_name(card['name']).endswith(' ex') and value.get('suffix') in (None,'ex'):value['suffix']='ex'
    for key in ('weaknesses','resistances'):
        for item in value.get(key,[]):
            if isinstance(item.get('value'),str):item['value']=re.sub(r'^[×xX]\s*(\d+)$',r'x\1',item['value'])
    return json.dumps(value,sort_keys=True,ensure_ascii=False)


def collapse(rows,quantities):
    from .functional_index import canonical_rank
    groups={}
    for row in rows:groups.setdefault(choice_signature(row['card']),[]).append(row)
    return [min(group,key=lambda r:(-quantities.get(r['functional_id'],0),canonical_rank(r['card']),r['functional_id'])) for group in groups.values()]


def label(row, peers):
    name=row['card']['name']
    if sum(normalized_name(r['card']['name'])==normalized_name(name) for r in peers)==1:return name
    def names(r):return [x.get('name','') for key in ('abilities','attacks') for x in r['card'].get(key,[])]
    components=names(row)
    # Describe the gameplay choice, never the collector/printing identifier.
    detail=next((x for x in components if x),'different effect')
    if sum(normalized_name(r['card']['name'])==normalized_name(name) and names(r)==components for r in peers)>1:
        card=row['card']
        # No full attack-text dumps. A compact printed distinction suffices.
        detail=next((a['effect'].split('.')[0] for a in card.get('attacks',[]) if a.get('effect')),next((str(a.get('damage',''))+' damage' for a in card.get('attacks',[]) if a.get('damage')),str(card.get('hp',''))+' HP'))
    return name+' — '+(detail[:64] or 'different effect')


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
    quantities={r['candidate_id']:r['quantity'] for r in (consensus or {}).get('cards',[])} if (consensus or {}).get('status')=='available' else {}
    pokemon=collapse(list({r['functional_id']:r for r in pokemon}.values()),quantities)
    observed=[r for r in pokemon if r['functional_id'] in quantities]
    source='user_selected' if explicit or regular else 'auto_buildaround'
    if observed:
        chosen=max(observed,key=lambda r:(strength(r),quantities[r['functional_id']],r['functional_id']))
        source='recent_consensus'
    else:
        ordered=sorted(pokemon,key=lambda r:(-strength(r),r['functional_id']))
        if len(ordered)>1 and strength(ordered[0])-strength(ordered[1])<=2:
            plausible=[r for r in ordered if strength(ordered[0])-strength(r)<=2]
            return core,dict(status='ambiguous',choices=[dict(candidate_id=r['functional_id'],canonical_name=r['card']['name'],label=label(r,plausible),aliases=[x['name'] for key in ('abilities','attacks') for x in r['card'].get(key,[]) if x.get('name')]) for r in plausible[:4]])
        chosen=ordered[0]
    return [r for r in core if r['card']['category']!='Pokemon']+[chosen],selection(chosen,source)


def selection(row,source):
    ability=next((a['name'] for a in row['card'].get('abilities',[]) if a.get('name')),None)
    return dict(status='selected',selected_core=dict(candidate_id=row['functional_id'],canonical_name=row['card']['name'],display_name=row['card']['name']+(' with '+ability if ability else ''),format='standard',selection_source=source,status='RESOLVED'))


REFERENT=r'(?:please )?(?:build (?:me )?(?:a )?(?:deck )?around (?:it|that card)|(?:build|make) (?:me )?(?:a )?deck (?:around|with) (?:it|that|that card)|use that one)'


def begin(request,history):
    """New explicit builds own selection context; old decks remain intact."""
    from .agent_consensus import build_request
    q=normalized_name(request.question).rstrip('.!?')
    if build_request(q) and not re.fullmatch(REFERENT,q):
        history=deepcopy(history)
        for key in ('selected_core','pending_build','build_clarification'):history.get('artifacts',{}).pop(key,None)
    return history


def prepare(request,history):
    """Resolve a gameplay choice/referent from bounded structured state."""
    artifacts=history.get('artifacts',{});pending=artifacts.get('pending_build') or artifacts.get('build_clarification')
    q=normalized_name(request.question).rstrip('.!?')
    if pending:
        choices=pending.get('choices',[])
        matches=[r for r in choices if q in [normalized_name(v) for v in (r['canonical_name'],r['label'],*r.get('aliases',[]))]]
        if len(matches)>1 or q in ('yes','yes please','sure','okay','ok') or re.fullmatch(REFERENT,q):
            # An ambiguous affirmation belongs to this pending theme. Ask its
            # concise choice again locally rather than guessing or using history.
            return request.model_copy(update={'question':pending['question'],'printing':None,'variant':None}),None
        if len(matches)==1:
            row=matches[0]
            core=dict(candidate_id=row['candidate_id'],canonical_name=row['canonical_name'],format='standard',selection_source='user_selected',status='RESOLVED')
            return request.model_copy(update={'question':pending['question']+' Selected build-around: '+row['canonical_name']+'.','printing':None,'variant':None}),core
        if q in ('no','no thanks'):
            return request.model_copy(update={'question':pending['question'],'printing':None,'variant':None}),None
    core=artifacts.get('selected_core')
    if core and re.fullmatch(REFERENT,q):
        return request.model_copy(update={'question':'Build me a Standard deck around '+core['canonical_name']+'.','printing':None,'variant':None}),core
    return request,None
