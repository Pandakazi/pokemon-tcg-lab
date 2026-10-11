"""Presentation-only labels for validated functional-card changes."""
from collections import defaultdict
import re


def change_lines(proposal, source_cards, preview_cards, source_candidates=()):
    """Use resolved facts; distinguish identities only within this change set.

    Never edit the proposal or infer a gameplay identity from a printing/name.
    The caller supplies the already validated source and composed preview.
    """
    preview={r['candidate_id']:r for r in preview_cards}
    candidates={r['candidate_id']:r for r in source_candidates}
    # Retained artifacts omit printed payloads. Reuse validated preview facts
    # for surviving cuts, or the retained identity's original candidate facts
    # for a fully removed card. This projection never changes stored artifacts.
    source={r['candidate_id']:dict(r,printed=r.get('printed') or
        preview.get(r['candidate_id'],{}).get('printed') or candidates.get(r['candidate_id'],{}))
        for r in source_cards}
    entries=[(label,item,(source if group=='removes' else preview)[item['candidate_id']])
        for group,label in (('removes','Cut'),('adds','Add')) for item in proposal[group]]
    groups=defaultdict(dict)
    for _,item,row in entries:
        groups[row['canonical_name'].casefold()][item['candidate_id']]=row

    def features(row):
        result=[]
        for field,kind in (('abilities','Ability'),('attacks','Attack')):
            for feature in row.get('printed',{}).get(field,[]) or []:
                name=' '.join(str(feature.get('name','')).split())
                if name and len(name)<=60:result.append((kind,name))
        return result

    def label(item,row):
        name=row['canonical_name'];siblings=groups[name.casefold()]
        if len(siblings)==1:return name
        other={text.casefold() for key,sibling in siblings.items() if key!=item['candidate_id']
            for _,text in features(sibling)}
        for kind,text in features(row):
            if text.casefold() not in other:return f'{name} — {kind}: {text}'
        # Only public set/collector identifiers, never functional keys/hashes.
        printing=row.get('printing_id','')
        if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*-\d+[A-Za-z0-9._-]*',printing):
            return f'{name} ({printing})'
        return name

    return [f"{kind}: {item['quantity']} × {label(item,row)}" for kind,item,row in entries]
