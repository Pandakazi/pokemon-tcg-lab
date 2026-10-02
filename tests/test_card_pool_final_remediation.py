"""Final PM numeric signal, synthesized mock answers, never historical prose."""
import json
import pytest
from pokelab import agent_research as a
from test_card_pool_remediation import envelope, reply, offline


@pytest.mark.parametrize('text,names',[
 ("Coalossal's Cragalanche does 150 damage and requires 1 Fighting and 3 Colorless Energy.",('Coalossal',)),
 ("Coalossal's Cragalanche requires 1 Fighting Energy and 3 Colorless Energy, does 150 damage, and discards 2 cards.",('Coalossal',)),
 ("Coalossal's Cragalanche costs four Energy and discards two cards.",('Coalossal',)),
 ("Coalossal has 180 HP.",('Coalossal',)),
 ("Centiskorch mills two cards while Deino mills one card.",('Centiskorch','Deino')),
 ("Crawdaunt's Snip Snip uses 2 coin flips. For each heads, discard the top card of your opponent's deck.",('Crawdaunt',)),
])
def test_supported_numeric_forms(text,names):
 assert a.assess(json.dumps(reply(text,names)),envelope()).outcome=='answered'


@pytest.mark.parametrize('text,names',[
 ("Coalossal has 150 HP.",('Coalossal',)), # A real damage number is not HP.
 ("Coalossal's Cragalanche does 180 damage.",('Coalossal',)),
 ("Coalossal's Cragalanche does 150 damage and needs 2 Fighting and 2 Colorless Energy.",('Coalossal',)),
 ("Coalossal mills 3 cards.",('Coalossal',)),
 ("Coalossal mills three cards.",('Coalossal',)),
 ("Crawdaunt uses 3 coin flips.",('Crawdaunt',)),
 ("Centiskorch deals 150 damage.",('Centiskorch','Coalossal')),
])
def test_unsupported_numeric_forms(text,names):
 with pytest.raises(a.ContractError) as exc: a.assess(json.dumps(reply(text,names)),envelope())
 assert exc.value.diagnostics['condition'] in ('unsupported_numeric_card_claim','unsupported_attack_cost')


@pytest.mark.parametrize('key',['simple','flagship'])
def test_grounded_synthesis_fixture(key):
 answer=reply('Centiskorch mills two cards while Deino mills one card.',('Centiskorch','Deino'))
 second=reply("Coalossal's Cragalanche also discards 2 cards and does 150 damage, with 1 Fighting and 3 Colorless Energy.",('Coalossal',))
 answer['facts']+=second['facts']
 answer['interpretation']=[dict(text='The printed discard quantities offer a starting point for comparing the amount removed, without establishing tournament strength.',evidence=answer['facts'][0]['evidence'])]
 result=a.assess(json.dumps(answer),envelope(key))
 assert result.outcome=='answered'
 assert not any(word in ' '.join(s.text for s in (*result.facts,*result.interpretation)) for word in ('DIRECT_MECHANICAL','score','rank'))


def test_competitive_comparison_remains_unsupported():
 with pytest.raises(a.ContractError) as exc:
  a.assess(json.dumps(reply('Coalossal is the better tournament card and a successful competitive choice.',('Coalossal',))),envelope())
 assert exc.value.diagnostics['condition']=='unsupported_competitive_claim'


def test_prompt_requests_synthesis_without_fixed_card_conclusion():
 assert 'rather than enumerate' in a.POOL_SYSTEM and 'Do not repeat the facts' in a.POOL_SYSTEM
 assert 'No fixed card list or ordering' in a.POOL_SYSTEM
 assert 'Coalossal' not in a.POOL_SYSTEM and 'Centiskorch' not in a.POOL_SYSTEM
