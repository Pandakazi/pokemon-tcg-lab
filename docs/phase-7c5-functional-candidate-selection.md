# Structured functional selection — PM QA candidate

Base: `27d66ec69184a0b46f6eebc9e0ba39a8a1fda617`.
Branch: `phase7c5-concrete-deck-resolution`. No live calls or certification.

## Proven ambiguity path

The sandbox exposed `functional_id`, but `agent_hybrid.parse()` constructed Candidate
with only name/printing/role/quantity. `Resolver.resolve_functional()` searched by name,
then attempted printing or attack/ability-name disambiguation. Two legal Milcery/Patrat
identities could therefore become ambiguous even though the model had received IDs.

## Contract change

Sandbox v2 renames the model-facing identity field to `candidate_id`; its value is the
existing gameplay identity (or existing Basic Energy identity). No identity migration
or second ID namespace. Existing v1 in-memory sandbox keys remain readable.

Existing name, printing hint, role and printed fields remain. Compact construction fields:
`ace_spec`, `basic_energy`, `copy_limit_name`, `requested_core`, and
`predecessor_candidate_ids` (selected legal name-matching predecessors). The existing
stage/evolveFrom fields remain. Retrieval/ranking, 48-entry and 14,000-byte candidate-list
bounds and overall prompt limits are unchanged; metadata counts toward the same budget.

The generated_deck block formerly carried card_name/printing_id/role/quantity. It now
accepts candidate_id/quantity without name or printing. Optional card_name (also name)
must match the chosen identity. Natural prose and the existing optional block remain.
The provider contract explicitly requests IDs, exact 60, at most one ACE SPEC copy,
name-level maximum four except Basic Energy, and preservation of the requested core.

Resolver order for generated lists:
1. Supplied ID must belong to this sandbox and still be legal in the functional index.
2. Optional name must match the canonical card name. Mismatch rejects the slot.
3. Resolve directly by ID and attach current canonical printing. Ignore provider printing
   hints on this path; do not rerun name ambiguity.
4. Without ID, preserve the existing unambiguous name/printing compatibility path.
   Bare-name functional ambiguity stays unresolved. Outside IDs never fall back by name.

The resolved report retains candidate_id alongside its existing card identity and canonical
printing. Collection storage, exact allocations and non-generated diff identity semantics
are untouched. Existing deterministic deck validation remains the final authority.

## Accounting and repair

Previously report.total_cards and repair.total counted only resolved copies. That is a
valid count of usable cards but not a count of all proposed slots. The new accounting
separates resolved_count, unresolved_proposed_count, proposed_total, true_missing_count,
and excess_proposed_count. Unresolved rows retain the requested candidate ID when present.
Repair includes missing_copies and typed construction_violations for name-copy excess
and ACE SPEC excess, alongside existing authoritative validation messages.

PM-equivalent deterministic fixture:
- 52 resolved + 3 ambiguous Milcery + 1 ambiguous Patrat = 56 proposed;
- true missing = 4, not 8;
- ACE SPEC count 2, maximum 1, excess 1;
- one repair picks explicit Milcery/Patrat IDs, supplies the genuinely missing copies,
  and resolves ACE SPEC excess; final result is 60, zero unresolved, VALIDATED.

Resolving an already proposed ambiguous named slot does not count as adding a second
missing slot. Repair distance credits those exact matching unresolved quantities once;
different-name replacements still count. Eligibility remains bounded to eight copies,
at most one pass; the existing actual edit bound and monotonic retention remain.
The UI's resolved count is not redefined, and no frontend changes were made.

## Tests and remaining limits

Focused integration run: 119 passed. Final focused module: 10 passed, covering direct
same-name ID selection, canonical printing despite a wrong provider hint, bare-name
ambiguity, unique-name fallback, name mismatch, unknown and known-but-unsupplied IDs,
one/two ACE SPEC behavior, PM-equivalent repair, and evolution predecessor links.
One final network-blocked gate: **756 passed**, including 381 research/card-pool/context,
16 functional-index and 45 Collection/Deck Builder compatibility tests. External sockets
and DNS were blocked; PM runtime settings were removed only from the test process.
`git diff --check` passed. Two existing dependency deprecation warnings only.
No frontend files changed, so no frontend suite/build was run.

Candidate relevance/strategic strength remains an independent limitation. This pass
changes selection and construction semantics, not ranking or archetype quality.
Additional metadata can reduce the number of candidates fitting the existing byte cap.
Evolution linkage is advisory, not a strategy engine or universal evolution validator.
No iterative retrieval, legal-policy changes, deck writes, UI/hover changes or Phase 7D.

Pre-existing uncommitted QA-launcher quoting edits are preserved outside this commit.
