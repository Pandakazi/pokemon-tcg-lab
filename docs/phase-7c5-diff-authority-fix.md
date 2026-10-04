# 7C.5 — Active-deck diff authority remediation

Starting commit: `80457faa0e3541c9d3d46fe23f576243b42789d7`, clean
`phase7c5-concrete-deck-resolution`. No live calls, retries, writes, merge or certification.

## Established cause

The exact follow-up “Okay. Make those changes concrete. What exactly comes out and
what exactly goes in?” matched none of the RECOMMEND patterns, so it selected
EXPLORE and the ordinary provider contract. No proposal was required. In contrast,
the direct request matched quantities and selected RECOMMEND. This is a locally
reproducible bypass, independent of any uncertain historical provider behavior.

Even when a diff was returned and validated, `assess` retained provider paragraphs
and `run` merely attached the checked report. There was no reconciliation between
prose such as “3rd Area Zero” and source-owned current quantities. Thus both bypass
and ignored validation at prose rendering were possible. Active-deck quantities
already existed in both input context and local validation; missing retrieval was
not the problem.

The direct request's historical unusable completion remains unexplained: PM supplied
the generic message, not provider_status/finish metadata. That branch precedes
proposal parsing and evaluation. No evidence establishes schema rejection versus
another provider failure. A fake successful completion proves local handling, not
live Gemini acceptance. No historical response was invented or replayed.

## Correction

- Both concrete phrasings select RECOMMEND. Ordinary EXPLORE routing is unchanged.
- Active-deck RECOMMEND requests require a diff in the Gemini wire schema, restrict
  kind to diff, exclude the unused full-list cards field, and require adds/removes
  and rationale. Provider-neutral instructions require deltas, not ordinal targets.
  Local parsing still degrades malformed/missing proposals to visible diagnostics.
- The final conversational quantity summary for a diff is server-rendered from
  the checked snapshot, never copied from provider prose. Each resolved change
  reports its source count and resulting count after the whole proposed diff.
- Missing diffs produce a visible unresolved message; role-only replacements remain
  unresolved. Invalid cuts, stale revisions, construction problems and advisory
  warnings stay visible. Nothing is silently applied or automatically retried.
- This narrow exact-diff summary intentionally replaces free-form proposal prose;
  the structured rationale remains model-authored metadata, not quantity authority.
  General conversational explanation is unchanged. No universal prose checker added.

## Verification

Focused gate: **77 passed** (after correcting a source-file encoding issue that
initially prevented collection). Fixtures use Area Zero Underdepths 3, Grass Energy
6, Night Stretcher 2, Cyrano 2, Jamming Tower 1 and Special Red Card 1 at revision 158.
Both direct and follow-up fake Gemini completions deliberately contain stale
ordinals. Final prose shows 3 → 4 and 6 → 7, removes vague alternatives, explicitly
labels an unresolved slot, and leaves all database bytes unchanged. Missing diffs
cannot leak unchecked exact prose. Existing tests cover repeated ordinary Gemini
conversation, concrete 60, invalid cuts, limits, stale revisions and malformed
proposals. One provider call per request remains asserted.

Single final network-blocked backend gate: **261 passed**, two existing dependency
deprecation warnings. Whitespace check passed.
No frontend changes: existing panel displays the canonical diff and corrected
server paragraphs. No frontend suite or build was necessary.

## PM retest

Restart the existing configured QA runtime at this commit. Verify ordinary deck
explanation still works. With revision 158 selected, repeat the direct exact-change
request and the reported follow-up. Check that current and resulting quantities
agree with the deck, unresolved slots are honest, and no state is written.
If a provider failure recurs, retain only `status`, `provider_status` and safe
execution metadata; its cause cannot be diagnosed from the generic UI message alone.

READY FOR PM LIVE QA; no claim that the historical provider failure is proven fixed.
