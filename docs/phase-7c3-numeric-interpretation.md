# Targeted numeric interpretation fix

Clean starting branch: `phase7c3-alternative-card-research` at `3548331682cdc1f12934cbda66cc55751fa81802`.

The historical rejected interpretation was not retained. Its safe diagnostic proves the numeric guard rejected it, but does not establish the exact sentence or number. Local deterministic reproduction establishes two defects:

- `Centiskorch mills 2 cards and Deino mills 1 card.` applied both numbers to both cited cards, yielding `unsupported_numeric_card_claim`. The equivalent `while` example already passed because it was split into explicit subject clauses.
- `Coalossal discards 2 cards but requires 4 Energy.` yielded `unsupported_attack_cost`: the cost precheck demanded an explicit attack name even though the named card had only one projected attack.

The fix splits a coordinated new explicit card subject after an existing numeric predicate. Shared subjects such as `Centiskorch and Deino mill 2 cards` remain together and must each support the value. Numbers are never pooled across citations. Card-level costs can use exactly one projected attack per named subject; multiple projected attacks remain ambiguous and require the attack name. Short `mills 1` wording now validates against printed discard quantities rather than accidentally matching another source number.

The same checks apply to facts and interpretation. Schema, citation membership and competitive boundaries are unchanged. Five prompt lines ask interpretation to use actual supported differences and explain their mechanical tradeoff rather than merely saying cards vary. No cards or desired conclusions are hardcoded.

Added 21 deterministic tests covering 2-vs-1 mill, Energy requirements, damage plus mill, multiple IDs and shared subjects, coin counts, swapped/unsupported values, absent/invalid citations, ambiguous attack costs, a comparative synthesis fixture and rejected competitive superiority. The frozen historical packet is reused unchanged.

Files: `src/pokelab/card_pool_research.py`, `src/pokelab/agent_research.py`, `tests/test_card_pool_interpretation.py`, and this report. No UI, retrieval, source-data, provider, qualification or certification changes.

Focused command (`PYTHONPATH=src`, existing canonical virtualenv Python, unique cache basetemp):

```powershell
python -m pytest -q tests/test_card_pool_interpretation.py tests/test_card_pool_final_remediation.py tests/test_card_pool_remediation.py tests/test_card_pool_research.py --basetemp $testTemp
```

Focused result: **97 passed**, 14.55 seconds. The single final regression gate adds selected-card/contract/deck-agent research, prior QA/limitation fixes, deck research, alternative retrieval and mechanics discovery (12 modules total). It replaces socket connect/connect_ex with a non-loopback rejection guard before invoking pytest; providers are mocked. Final result and ending SHA are recorded in the handoff. Existing dependency deprecation warnings are unrelated. No frontend suite was needed because frontend files were untouched.

Final gate: **414 passed**, 40.60 seconds. `git diff --check` passed. **READY FOR PM LIVE QA.**

No live provider calls, external network calls, automatic retries, merge, tag, main changes or certification. Deterministic fixtures establish supported comparisons can pass; they do not guarantee a model's future prose quality. PM should retest the same opponent-mill question after restarting the existing QA runtime, checking actual comparative interpretation and safe diagnostics if rejected.
