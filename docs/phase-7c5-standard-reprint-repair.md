# Phase 7C.5 Standard reprint resolution and monotonic repair

Base: `793e64259e4bc13ed65521aa664d0ff7bb5fa9fb`.

## Confirmed causes and scope

The recovered live response establishes that repair dropped one Call Bell (`sv08-165`), reducing the resolved artifact from 24 to 23 without a replacement. The orchestration previously committed any returned repair list, including a worse incomplete result.

There are two distinct resolver defects. Formatting-only differences in effect text split legal Ultra Ball printings into multiple functional groups. Separately, `name_printing_mismatch` is an early rejection when a supplied ID names a different card; it is not the formatting-ambiguity condition. The recovered summary does not contain those erroneous provider IDs, so their exact original targets cannot be reconstructed.

The listed final entries sum to 23 resolved plus 35 rejected cards (58 proposed), with 37 remaining to reach 60 after rejection. Correcting a printing alone does not establish complete construction.

## Resolution change

`engine.functional_signature` supports optional recursive whitespace-only normalization for gameplay comparison. The default remains byte-for-byte compatible with the previous signature calculation. Existing collection, saved-deck, active-deck and Library IDs are not migrated or rewritten.

Generated-list resolution compares formatting-normalized gameplay signatures, filters Standard-legal groups, and deterministically selects an existing legal printing. Returned card IDs remain established deck identities. Names alone never merge distinct gameplay records. Different wording, numeric effects, attacks, and other functional fields remain distinct.

For generated lists only, a missing or mismatched provider ID is treated as an unusable printing hint: the supplied card name must independently resolve to one supported legal gameplay identity. Ambiguity remains unresolved; an invented name cannot borrow the unrelated printing's identity. An exact same-name historical printing expands only to formatting-equivalent records, not arbitrarily to a different effect. Active-deck cuts and exact factual lookup retain strict mismatch behavior.

Same-effect replacement is reached only after this identity/legal-printing resolution attempt. No prompt, UI, evidence-presentation, retrieval algorithm or routing changes were made.

## Read-only live-cache findings

The documented QA card cache was read at `C:/Users/Mike/Documents/pokemon-tcg-lab/data/cards.sqlite3`; its records were checked September 23, 2026. These are local evidence findings, not an external verification of current tournament legality.

- Ultra Ball: legal `me01-131`, `me02.5-213`, `me02.5-264`. Generated name-only and bad-ID resolution now choose `me01-131`. The two legal signatures differed only in paragraph whitespace. Historical `sv01-196` and `swsh9-150` have supported legal counterparts; genuinely different old wording is not silently equated.
- Pidgey, Pidgeotto, Pidgeot ex, Professor's Research, Super Rod, Town Store: no Standard-legal printing flagged in this cache. Correcting a mismatched ID does not make them legal. Thus no other recovered mismatch name becomes a legal resolved slot through formatting normalization.
- Lumineon V, Lost Vacuum, Double Turbo Energy: records exist, but no cached Standard-legal printing. Bad-ID recovery can identify the intended name, but does not waive legality.
- Previously inspected Natu, Xatu, Arven, Iono, Nest Ball, Technical Machine: Evolution and Defiance Band likewise lack cached Standard-legal support.

## Monotonic repair

An incomplete repair with fewer resolved cards than the supplied baseline is rejected before session/artifact persistence. For the initial bounded repair, the original incomplete artifact survives with `repair_regressed` metadata. For an explicit pending-artifact follow-up, the previous stored artifact is returned as a labelled historical/incomplete snapshot and remains available for recount. It is not newly certified against changed data.

A successfully validated complete result is still accepted. This pass does not add an automatic exception allowing unexplained removal of previously resolved cards from an incomplete artifact. Any deliberate invalidation requiring a lower baseline must be explicitly reviewed rather than silently committed.

## Verification

- Existing focused resolver/FINALIZE tests: 85 passed.
- New focused regressions: 7 passed after completing synthetic fixture metadata.
- Single final network-blocked backend gate: 377 passed in 93.38 seconds, including deck allocation and collection compatibility. Two existing dependency deprecation warnings only. git diff --check passed.
- No frontend changes or frontend run.
- No external network/provider calls, workspace writes, merge, tag or certification.

PM should retest a generated Standard deck containing Ultra Ball and a pending partial repair. Full completion remains dependent on valid model choices and local legal-card coverage; this fix does not guarantee that the historical out-of-format list can be completed without changing its card choices.
