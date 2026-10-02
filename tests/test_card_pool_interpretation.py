"""Numeric synthesis uses each cited subject's evidence, never pooled values."""
import json
import pytest
from pokelab import agent_research as a
from pokelab.deck_research import fields
from pokelab.research_grounding import fields as values
from test_card_pool_remediation import envelope, reply, offline


def synthesis(text,names):
    answer=reply(text,names)
    answer['interpretation']=answer['facts'];answer['facts']=[]
    return json.dumps(answer)


@pytest.mark.parametrize('text,names',[
 ('Centiskorch mills 2 cards while Deino mills 1.',('Centiskorch','Deino')),
 ('Centiskorch mills 2 cards and Deino mills 1 card.',('Centiskorch','Deino')),
 ('Centiskorch mills two cards, but Deino mills one.',('Centiskorch','Deino')),
 ('Coalossal discards 2 cards but requires 4 Energy.',('Coalossal',)),
 ('Centiskorch requires 1 Energy and Coalossal requires 4 Energy.',('Centiskorch','Coalossal')),
 ('Coalossal deals 150 damage and discards 2 cards, while Cornerstone Mask Ogerpon deals 100 damage and discards 1 card.',('Coalossal','Cornerstone Mask Ogerpon')),
 ('Coalossal deals 150 damage and discards 2 cards and Cornerstone Mask Ogerpon deals 100 damage and discards 1 card.',('Coalossal','Cornerstone Mask Ogerpon')),
 ('Centiskorch and Coalossal discard 2 cards.',('Centiskorch','Coalossal')),
 ('Crawdaunt flips 2 coins and deals 40 damage, while Coalossal deals 150 damage and discards 2 cards.',('Crawdaunt','Coalossal')),
])
def test_supported_interpretation(text,names):
    assert a.assess(synthesis(text,names),envelope()).outcome=='answered'


@pytest.mark.parametrize('text,names',[
 ('Centiskorch mills 1 card and Deino mills 2 cards.',('Centiskorch','Deino')),
 ('Centiskorch and Deino mill 2 cards.',('Centiskorch','Deino')),
 ('Coalossal discards 3 cards but requires 4 Energy.',('Coalossal',)),
 ('Coalossal discards 2 cards but requires 3 Energy.',('Coalossal',)),
 ('Coalossal deals 100 damage and Cornerstone Mask Ogerpon deals 150 damage.',('Coalossal','Cornerstone Mask Ogerpon')),
 ('Crawdaunt flips 3 coins and deals 40 damage.',('Crawdaunt',)),
 ('Cornerstone Mask Ogerpon mills 3.',('Cornerstone Mask Ogerpon',)), # Do not borrow its cost count.
])
def test_wrong_interpretation(text,names):
    with pytest.raises(a.ContractError) as exc: a.assess(synthesis(text,names),envelope())
    assert exc.value.diagnostics['condition'] in ('unsupported_numeric_card_claim','unsupported_attack_cost')
    assert exc.value.diagnostics['path']==['interpretation',0,'text']


@pytest.mark.parametrize('references',[[],['ev-not-supplied']])
def test_uncited_interpretation_rejected(references):
    answer=json.loads(synthesis('Centiskorch mills 2 cards.',('Centiskorch',)))
    answer['interpretation'][0]['evidence']=references
    with pytest.raises(a.ContractError): a.assess(json.dumps(answer),envelope())


def test_other_card_citation_does_not_license_comparison():
    with pytest.raises(a.ContractError) as exc:
        a.assess(synthesis('Centiskorch mills 2 cards and Deino mills 1 card.',('Centiskorch',)),envelope())
    assert exc.value.diagnostics['condition']=='uncited_candidate_claim'


def test_card_cost_with_multiple_projected_attacks_requires_named_attack():
    e=envelope();item=next(i for i in e.packet.evidence if values(i.model_dump()['fields'])['name']=='Coalossal')
    data=values(item.model_dump()['fields'])
    data['components'].append(dict(component='attack',name='Other attack',text='',structured={'cost':['Fighting']}))
    changed=item.model_copy(update={'fields':fields(data)})
    e=e.model_copy(update={'packet':e.packet.model_copy(update={'evidence':tuple(changed if i.id==item.id else i for i in e.packet.evidence)})})
    with pytest.raises(a.ContractError) as exc: a.assess(synthesis('Coalossal requires 4 Energy.',('Coalossal',)),e)
    assert exc.value.diagnostics['condition']=='unsupported_attack_cost'


def test_comparative_fixture_and_competitive_boundary():
    text='Centiskorch mills 2 cards while Deino mills 1. The printed discard amount is a useful distinction when researching direct mill; it does not establish tournament strength.'
    assert a.assess(synthesis(text,('Centiskorch','Deino')),envelope()).interpretation[0].text==text
    with pytest.raises(a.ContractError) as exc:
        a.assess(synthesis('Centiskorch is the better competitive choice.',('Centiskorch',)),envelope())
    assert exc.value.diagnostics['condition']=='unsupported_competitive_claim'
    assert 'rather than merely saying the' in a.POOL_SYSTEM
