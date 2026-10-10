"""Read-only PTCGL text export from local printing/set metadata."""
from contextlib import closing
import json
import re
from pydantic import BaseModel,ConfigDict,Field
from .library_identity import library_signature


class ExportRow(BaseModel):
    model_config=ConfigDict(extra='forbid')
    printing_id:str=Field(min_length=1,max_length=100)
    quantity:int=Field(strict=True,ge=1,le=9999)


class ExportRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    cards:list[ExportRow]=Field(min_length=1,max_length=120)


class ExportUnavailable(ValueError):
    pass


ENERGY_SYMBOLS=dict(Grass='G',Fire='R',Water='W',Lightning='L',Psychic='P',Fighting='F',Darkness='D',Metal='M',Fairy='Y')


def printing_line(card,metadata):
    # Online code is authoritative for subsets: BRS + TG01, not BRS:TG.
    abbreviation=metadata.get('abbreviation')
    code=metadata.get('tcgOnline') or (abbreviation.get('official') if isinstance(abbreviation,dict) else None)
    number=str(card['localId'])
    if ((metadata.get('serie') or {}).get('id')=='tk' or not isinstance(code,str)
        or not re.fullmatch(r'[A-Z0-9]+(?:-[A-Z0-9]+)*',code)
        or not re.fullmatch(r'(?:[0-9]+|[A-Z]+[0-9]+[A-Z]?)',number)):
        raise ExportUnavailable('The exact printing has no supported local PTCGL set-code/collector mapping.')
    # Ordinary zero-padded numeric tokens become Live's numeric collectors.
    # Subset/promo tokens (TG01, GG01, SWSH001, etc.) remain intact.
    if number.isdecimal():number=str(int(number))
    name=card['name']
    basic=library_signature(card)
    if basic.startswith('library-basic-energy:'):
        kind=basic.split(':',1)[1];name=f'Basic {{{ENERGY_SYMBOLS[kind]}}} Energy'
    if not name.strip() or any(ord(c)<32 or ord(c)==127 for c in name):
        raise ExportUnavailable('The local card name cannot be represented as a single export line.')
    return name,code,number


def export_ptcgl(cards,request):
    """All-or-nothing serialization; never changes allocations or preferences."""
    with closing(cards.connect()) as db:
        marks=','.join('?' for _ in request.cards)
        rows=db.execute(f"SELECT c.id,c.raw,s.raw metadata FROM cards c LEFT JOIN sets s ON s.id=c.set_id WHERE c.game='tcg' AND (c.id IN ({marks}) OR (c.category='Energy' AND json_extract(c.raw,'$.energyType')='Normal'))",
            [row.printing_id for row in request.cards]).fetchall()
    catalog={r['id']:(json.loads(r['raw']),json.loads(r['metadata']) if r['metadata'] else {}) for r in rows}
    output=[];warnings=[]
    for row in request.cards:
        if row.printing_id not in catalog:raise ExportUnavailable('A selected printing is not in the local TCG catalog.')
        card,metadata=catalog[row.printing_id]
        try:line=printing_line(card,metadata)
        except ExportUnavailable:
            basic=library_signature(card)
            if not basic.startswith('library-basic-energy:'):raise
            # Explicit export-only substitution for unrepresentable Basic Energy.
            # Use locally indexed SVE metadata; never synthesize a set/collector.
            candidates=[]
            for candidate,meta in catalog.values():
                if library_signature(candidate)==basic:
                    try:
                        candidate_line=printing_line(candidate,meta)
                        if candidate_line[1]=='SVE':candidates.append((int(candidate_line[2]),candidate_line))
                    except (ExportUnavailable,ValueError):continue
            if not candidates:raise ExportUnavailable('No locally mapped Basic Energy equivalent is available for PTCGL export.') from None
            line=min(candidates,key=lambda c:c[0])[1]
            warnings.append(f'{card["name"]}: the exact printing is unavailable for export; copied {line[1]} {line[2]} as an equivalent Basic Energy. PokéLab allocations are unchanged.')
        output.append((card['category'],line,row.quantity))
    # Merge only identical external representations; retain every source quantity.
    grouped={category:{} for category in ('Pokemon','Trainer','Energy')}
    for category,line,quantity in output:
        grouped[category][line]=grouped[category].get(line,0)+quantity
    sections=[]
    for category,entries in grouped.items():
        sections.append(f'{"Pokémon" if category=="Pokemon" else category}: {len(entries)}')
        sections.extend(f'{quantity} {name} {code} {number}' for (name,code,number),quantity in entries.items())
        sections.append('')
    total=sum(row.quantity for row in request.cards)
    sections.append(f'Total Cards: {total}')
    return dict(text='\n'.join(sections),warnings=list(dict.fromkeys(warnings)),total=total,
        category_totals={category:sum(entries.values()) for category,entries in grouped.items()})
