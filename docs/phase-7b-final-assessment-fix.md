# Phase 7B final correctness fix — awaiting final PM authorization

PM accepts the current qualification coverage as sufficient for Phase 7B.
No further live qualification is required before certification. This change
implements only the remaining internal-assessment failure invariant.

## Exact behavior

- JSON syntax errors and duplicate keys caught during answer JSON parsing, or
  Pydantic validation errors caught while validating Answer, remain definitive
  output-contract FAIL with output_valid false and bounded structural diagnostics.
  Grounding/citation/rules fields are null because those checks did not run.
- Any other parsing/validation/evaluation exception becomes NOT_EVALUATED /
  INDETERMINATE_ASSESSMENT_FAILURE. All output/grounding/citation/rules fields are
  null, hallucinations/usefulness NOT_EVALUATED, answer null, no unsupported-claim
  inference. The only diagnostic is a fixed internal_assessment_error category.
- The exception classes are caught at the specific validation operation; a
  ValidationError thrown by later evaluator code is internal, not a model FAIL.
- A final boundary around assess also catches an unexpected entry-point failure.
  Provider/model, suite/hashes and safe execution timing/finish/token/cost fields
  already in the run record remain intact. No raw exception or model text is saved.
- An internal failure stops a live batch before another model and yields nonzero
  CLI exit status. There is no automatic retry, fallback or recovery inference.
- Completed assessments retain the exact existing grounding, citation, rules and
  PM-review criteria. V1/v2 prompts, contracts, hashes, routing, output ceilings,
  price controls and historical qualification records are unchanged.

## Verification

152 network-blocked tests passed: 126 provider/harness tests and 26 certified 7A
regression cases. Includes injected parser, schema, evaluator, diagnostic and
entry-point exceptions; definitive malformed JSON/missing/wrong-type/duplicate
contract failures; metadata preservation; safe diagnostics; batch stop; CLI exit;
and existing frozen hash, serial execution and secret quarantine checks. Two
existing dependency deprecation warnings remain. No network or live model call.

## Proposed certification closeout — do not execute yet

1. After final PM authorization, verify the clean development branch and accepted
   fix commit, frozen input/packet and both suite/configuration hashes. Snapshot
   previous certification tag object/target SHAs for preservation verification.
2. Reconcile main/roadmap documentation only to record PM certification of the
   bounded Phase 7B scope and the accepted qualification matrix. Keep Gemini v2
   indeterminate, Nemotron v1 output-limited and other unqualified results intact.
   Commit only any necessary certification documentation.
3. The development checkout's origin currently points to an older local phase4
   checkout. Use the canonical repository at C:/Users/Mike/Documents/pokemon-tcg-lab
   (origin https://github.com/Pandakazi/pokemon-tcg-lab.git). Fetch/reconcile the
   accepted branch from this checkout into the canonical repository, then inspect
   remote state and ancestry. Prefer fast-forward-only main; stop and report any
   unexpected divergence or dirty state rather than force/reset/rewrite history.
   Local development main is currently an ancestor, but remote state must be
   verified at closeout time. No remote fetch/push was performed in this fix.
4. Push final main and phase7b-provider-qualification to the canonical remote.
   Proposed annotated tag: phase-7b-provider-qualification-certified-2026-09-26
   (use the actual PM-approved certification date if different). Target the final
   certified main after documentation closeout. Never move an existing tag.
5. Verify local/remote main and development branch SHAs, annotated tag object and
   peeled target, all prior certification tags unchanged, and relevant working
   trees clean. Report exact SHAs and documentation commit. Do not rerun live
   models or broad engineering suites merely for closeout.
6. Stop after closeout. Phase 7C Research Mode requires its own scope/authorization;
   no provider expansion, routing intelligence or 7C implementation is included.

This plan is a proposal only. No certification declaration, merge, tag, push or
7C work was performed. STOP for final PM authorization.
