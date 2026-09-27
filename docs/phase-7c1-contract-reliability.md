# Phase 7C.1 contract reliability investigation

Starting commit: `fff9dedfce001f07be7eec24e9f938eaebf4b81d` on
`phase7c1-selected-card-research`.

## Historical findings

The exact rejection causes for Risky Ruins (role), Budew (matchups), and Crispin
(removal) are each **historically indeterminate**. The inspected current local
access log contains 17 Research POST responses with HTTP 200, but no retained
structured contract diagnostics or rejected answers. HTTP 200 alone does not
establish product success or a provider-call count. Neither question wording nor
the successful examples establishes what any discarded response contained.

Offline reconstruction of Risky Ruins, `me01-127` normal, revision 157, 30-day
window, date 2026-09-26, and the supplied exact question matches evidence hash
`e8af5126171eaf854d975fd5dbce5cafa392f20e4a9ea14f354f90df205a551e`
(17,033 bytes). This reconstructs evidence, not provider output.

At the inspected implementation, the reported generic rejection message maps to
an answer-contract failure after the normal-completion gate. JSON/schema,
citation-membership and answer-shape checks can cause it. Internal assessment,
transport and truncation failures have separate statuses. No retained result
identifies which contract check failed in these three transactions. The product
validator does not independently assess semantic grounding or citation entailment;
these failures must not be described as demonstrated grounding failures.

## Established defect and bounded correction

The server already returns bounded `contract_diagnostics`, but the Agent panel's
result type and presentation ignored that field. The panel therefore collapsed
distinguishable safe failures to one generic message. This is an observability
defect, not proof of an answer-acceptance defect or provider noncompliance.

The only production change adds an expandable Validation details disclosure for
contract/internal-assessment failures. It renders static allowlisted condition,
field and error labels, boolean parsing/schema results and bounded citation
counts. Error arrays and paths are capped. Arbitrary fields, values, exception
messages, rejected output and hidden reasoning are not rendered. No persistence,
retry or new request is added. Existing alerts and answer withholding remain.

No deterministic contradiction or incorrect rejection of a valid contract was
established. Prompt, schema, parser, citations, provider transport, evidence
selection, budgets and authority boundaries remain unchanged. This correction
will make a future authorized failure diagnosable; it does not claim to improve
model output compliance or recover the historical causes.

## Verification

Focused backend: 130 tests passed. Focused Agent panel: 11 tests passed.
The three reported question shapes are exercised with synthetic local cards and
fake valid/schema-invalid/provenance-citation responses (nine cases). These test
plumbing, classification, one call and unchanged databases, not unknown historical
responses or strategic quality. Existing contract-boundary and reconstructed
Budew regressions remain intact. UI tests cover JSON/schema/citation/internal
details, bounded rendering, arbitrary-data quarantine and no automatic retry.

One final backend regression gate: 536 passed (two dependency deprecation
warnings). Full frontend suite: 81 passed. TypeScript and production build passed.
The full backend gate blocks external sockets; provider tests use fake transports.
Frontend tests mock API calls. No live network/provider calls or runtime restart
were made. Native disclosure behavior is covered by focused rendered-component
tests; no browser automation was necessary for this small text-only disclosure.

The retained Budew fixture/hash remains unchanged:
`991a77f9439050275916f1933a169b7a5d886a4b1874c601e3381d9a2eb819f1`.
Phase 7A/7B source contracts and qualification artifacts remain identical to the
certified base; qualification tree:
`1743d4acc87cb1a00188804aa6d55b1f085cfab0`.

The pre-existing uncommitted `phase-7c1-live-call-2-baseline.md` is preserved
byte-for-byte and included as documentation, not used to infer these failures.
Its SHA-256 is
`8a2cf357e8276ff5e953f215e42f9ea209e763d1ad6c162566f2b0421f8d4fda`.
Its earlier log observation is historical; the access log has since accumulated
additional entries. Its prior closeout recommendation is not a certification or
a finding that these subsequent failures are resolved.

## PM decision and untouched backlog

Ready for PM review/retest of diagnostic visibility. The cause of the repeated
historical answer failures remains unresolved, not an accepted provider limitation.
Any future live retest requires separate authorization. No merge, tag,
certification, or Phase 7C.2 work was performed.

Preserved non-blocking backlog, with no implementation in this pass:

- robotic prose;
- deterministic partner-text relevance ranking instead of identity order;
- clearer mechanics versus empirical co-occurrence distinction;
- card clicks automatically updating Agent context;
- clearing question input on card-context changes;
- deck-level questions without selected cards;
- later 7C.3 alternative-card research;
- strategy/piloting knowledge;
- occasional PowerShell keyboard-input loss during QA restart.
