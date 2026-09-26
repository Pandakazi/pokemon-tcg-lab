# Research → Copy to Deck Builder

Post-Phase-6 integration for PM QA, not merged or certified. Branch
`phase6-copy-to-deck-builder`, based on certified main
`348a6968ebc5b25e49ac9ea82b77379a40fede25`.
The Phase 6 certification tag and its historical scope remain unchanged.

## Operation and safety

`POST /api/v1/deck-workspace/copy-research` accepts schema_version 2, current
workspace revision, source (`tournament` or `composite`), stable research key,
window (`7`, `30`, `90`, `format`; default `30`) and optional explicit discard.
Quantities are loaded server-side from existing research resources, not supplied
by the browser. No ingestion, research algorithm or identity changes.

The domain operation `Decks.copy_research` resolves the complete list, then uses
one SQLite BEGIN IMMEDIATE transaction with the existing workspace schema:

1. Check the optimistic revision and dirty-draft guard.
2. Resolve every functional quantity into certified deck keys and exact allocations.
3. Create a new UUID and deterministic metadata-based name, capped at the existing
   100-character limit. Tournament: archetype/player/event; composite: archetype
   plus “Archetype Composite”.
4. Insert one new saved deck and activate the same complete document, incrementing
   the workspace revision once. Existing saved rows and printing preferences stay intact.
5. Build the normal Deck Builder response and run its authoritative validator before
   commit. Any error rolls back all deck writes, including post-write response failures.

A dirty draft requires the existing style of explicit discard confirmation. Cancel
preserves it; users can save first through Deck Builder. Confirmation discards only
unsaved draft changes, never an existing saved version. A conflicting revision
returns 409 without writing. Copy opens `/deck-builder` after success and survives
reload immediately without an extra Save. Copied decks are editable normally.

The implicit-addition preferred-printing resolver is shared with the existing
quantity operation. Valid stored preferences win; otherwise the research resource's
Library representative and its normal default-variant mechanism provide local
presentation. These choices do not assert source exact printing/finish provenance.
Curated Basic Energy quantities aggregate by the established type-based deck key.
No collection ownership or preferred-printing data is written; unowned cards are allowed.

Tournament lists copy faithfully, including lists the current validator considers
invalid. There is no repair, trimming or substitution. Composite copy uses the
existing validated Phase 6 result for the selected timeframe. Research stays immutable.

## Failure and limitations

Only complete mapped 60-card resources can be copied. Unmapped, unavailable,
missing-printing or unsafe-identity resources are disabled/refused, never truncated.
The research page remains open on failure and offers an active-deck reload before
retry. A transport failure may occur after a successful commit; reload the active
deck before retrying to avoid creating an intentional second copy. Atomicity does
not imply network-level exactly-once delivery.

The server resolves current cached evidence on click. Composite source refreshes
can change its current result; no historical composite snapshots are introduced.
No new autosave/recovery system, schema migration, validator, Phase 6.5, Rules or
Agent work is included. Existing saved decks are not overwritten by copy.

## Focused verification and PM walkthrough

New backend tests cover tournament/composite quantities, non-default exact printing
and finish, Basic Energy, saved rows/defaults/ownership/evidence preservation,
dirty/stale guards, missing printing, incomplete evidence, post-write rollback,
faithful invalid tournament copying and typed API rejection.
Browser coverage uses fresh isolated databases and real cached main-Limitless lists.
It covers both buttons, new deck IDs, 60-card functional counts, saved-deck safety,
reload/editing, ownership/source immutability, cancellation, errors and unavailable copy.

1. Restart this checkout with `scripts/Start-Phase6-QA.ps1 -Action Restart`.
2. Open http://127.0.0.1:5175/deck-builder and hard-refresh (Ctrl+Shift+R).
   Verify `/api/v1/deck-workspace` runtime_revision matches this branch's HEAD.
3. Save the current draft if wanted. Open a card's research, an archetype, then a
   Tournament Deck. Select **Copy to Deck Builder**.
4. Confirm the new metadata-based name and 60-card list. Check Open still lists
   previous saved decks. Edit a quantity and reload to verify normal persistence.
5. Return to the archetype. Select **Copy Composite to Deck Builder**. With a dirty
   draft, first cancel and verify preservation; save first or explicitly confirm.
6. Check selected preferred printing/finish, unowned cards, validation, and unchanged
   source quantities. Format without configuration and partial lists cannot copy.

Runtime verification is read-only against permanent PM data; mutation checks use
isolated test data. The accepted Phase 6 tag is not modified. Final acceptance is Mike's.
## Final UX polish — tray List/Gallery

Frontend-only presentation enhancement on the Copy-to-Deck-Builder branch. List
remains the default and keeps its existing controls and metadata. Gallery displays
one artwork tile per functional entry using the existing resolved allocation anchor,
with total quantity and the same +/- and Remove commands. Mixed exact allocations
remain intact and inspectable in List. Images reuse CardImage/FinishImage and the
existing 500 ms, image-bounds-only competitive popup with active-deck counts.

Tray view lives in DeckProvider presentation state, survives in-app Card Detail and
research navigation and carries over to newly copied decks. Reload/restart resets
to List; no new preference store was introduced. Switching views never writes deck,
collection, preferences or validation data. Missing artwork has a readable fallback.

Focused verification: 10 existing frontend tests, five targeted browser checks,
TypeScript and production build passed. Browser coverage checks view toggling,
identical quantities, bidirectional +/- updates, navigation, hover boundary/timing,
non-mutating toggles and both copied source types retaining Gallery. No backend
code changes or backend suite reruns. PM QA: toggle List/Gallery in the active tray,
change quantities, inspect artwork, follow research links, copy either source type,
and return to List to inspect exact allocations. Final acceptance remains Mike's.
