# Pre-Ally Settings — PM QA handoff

Historical handoff for settings candidate `35296ba1b344413fa5ef8c9b5a3332ce366258f6`.
The current Gemini-only preview and custom-proposal completion are documented in
[the final pre-Ally PM QA handoff](pre-ally-custom-proposal-qa.md).

Starting candidate: `1fefc3486c95dab97fe313fa0b32285b9c4c0ae3`.
Branch: `phase7c5-concrete-deck-resolution`.

Status: **READY for PM QA of these bounded settings features**. This is not release certification; the pre-existing fixture failures and live provider smoke test remain documented below.

## Implemented behavior

- Top-level Settings gear opens Agent Settings or Appearance.
- Agent Settings selects exactly one of OpenAI/Gemini, accepts a password-masked API key, and streams real transaction stages: validation, connection, response check, secure save, connected.
- Test & Apply makes one bounded 64-output-token connection request through the existing adapter. Failure preserves the previously active and saved configuration. No retry, failover or provider routing is added.
- Windows uses the existing user-bound DPAPI implementation. The provider, model and key are saved together atomically in `%LOCALAPPDATA%/PokeLab/agent-settings/web-agent.secret`, separately from the legacy desktop credential and outside the checkout/database paths. No key is written to browser storage, a plaintext settings file or environment variables. Unsupported platforms keep credentials only in server memory for the session. A Windows encryption/save failure does not fall back to plaintext or silently switch providers.
- Replace Key requires another successful test. Disconnect overwrites the encrypted record with a disabled record containing no key. The disabled record prevents environment configuration from silently reconnecting after restart. It does not revoke the key at the provider.
- Existing environment configuration remains effective until the user applies or disconnects through Settings. Fixed model defaults are `gpt-4.1-mini` and the existing `gemini-3.5-flash-lite`. Matching existing research-model or provider-model configuration is honored. No model picker is added. OpenAI compatibility was checked against [official model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
- Settings transactions share the existing Agent single-flight lock. In-flight requests cannot be interrupted by a switch/disconnect. Product credentials and opt-in are request-local; the qualification harness retains its existing zero-cost gates. Paid product requests no longer report an invented zero-cost estimate.
- Existing Agent panels refresh status after settings changes without clearing conversational turns, selected cards or deck context.
- Appearance defaults to System, follows device changes, and persists System/Light/Dark in local browser storage. It applies before React renders to prevent the wrong theme flashing. Disabled browser storage yields a session-only preference.

## Architecture and theme scope

Provider selection previously came from `POKELAB_RESEARCH_*` environment settings, with credentials in provider-specific environment variables. The existing desktop DPAPI `SecretStore` was reusable. The new web settings manager supplies selection/credentials at the existing provider boundary; Agent generation, consensus, deck completion, collection, sync and deck mutations are unchanged.

Hard-coded colors were concentrated in `web/src/index.css` and `web/src/Shell.tsx`, so a centralized palette was feasible in those two existing files. Shared shell, filters, gallery/list, details, collection, deck tray and Agent surfaces now use light/dark variables. Chart-series colors, brand accents, card artwork, magnification and foil/light effects retain their authored colors. No broad component rewrite, art inversion or filter is used. External fonts and remote card art were blocked/replaced with local placeholders in the settings screenshot tests; the existing finish/browser tests exercise real card artwork separately.

## Files changed

- `src/pokelab/agent_settings.py`: encrypted settings, transactional apply/disconnect, progress.
- `src/pokelab/agent_providers.py`: request-local product credential/authorization integration and honest cost metadata.
- `src/pokelab/agent_research.py`: optional settings binding at the existing service boundary.
- `src/pokelab/api.py`: bounded local-only settings status, streamed Test & Apply, Disconnect endpoints; sanitized validation/errors.
- `web/src/Settings.tsx`: settings menu, native modal, provider status and credential UX.
- `web/src/Appearance.ts`: theme persistence and System preference handling.
- `web/src/AgentStatus.ts`: settings-change/status notifications.
- `web/src/Shell.tsx`: gear/status and shared palette tokens.
- `web/src/ConversationPanel.tsx`, `web/src/ResearchAgent.tsx`: status refresh only.
- `web/src/index.css`: centralized palette and settings styling.
- `web/index.html`: persisted/System appearance initialization before first render.
- `tests/test_agent_settings.py`: focused backend/security/DPAPI tests.
- `web/src/Settings.test.tsx`: focused UX, progress, failure, persistence and conversation-preservation tests.
- `web/integration/settings.spec.ts`: native browser modal, exact theme colors, navigation and artwork preservation.
- `docs/pre-ally-settings-qa.md`: this handoff.

The pre-existing `scripts/Start-Phase5-QA.ps1` edit is excluded from task changes. Its SHA-256 remains `BB800264286E41FB5C080A817D7136A69F1796C79568CABFD5548C6782B32356`.

## Verification

- Focused backend: **30 passed**, including actual Windows DPAPI encryption/reload/disconnect with a dummy key, secure-save failure preservation, both providers, request-local isolation, single-flight behavior, origin/Host/JSON/size guards and sanitized errors.
- Focused frontend: **8 passed**.
- Full frontend: **135 passed**. Typecheck and production build passed after the final palette correction.
- Settings + preview browser run with fresh state: **6 passed**, including both new settings tests, artist discovery, copy/export, competitive sync and disabled Analytics.
- Broader browser run: **18 passed, 2 failed** across 20 Library, Collection, Deck Builder, finish, preview and Settings checks. The Collection failure assumed empty state after earlier Collection tests populated it; the isolated preview rerun passed. The dense-deck failure expects an obsolete “No AI provider is connected” message. That same assertion fails in the unchanged starting-SHA product snapshot; a test-only local-artwork route was used to remove CDN availability from the comparison. No production or existing test assertion was changed in the current checkout.
- Original full backend run: **1,354 passed, 10 failed**. Removing inherited `POKELAB_GEMINI_FREE_TIER_CONFIRMED` only for test processes fixes the qualification expectation. The nine remaining failures are pre-existing research/copy fixture failures.
- Unchanged starting-SHA snapshot and modified checkout, same three backend test groups under the same controlled environment: **149 passed, 9 failed** in each. The same assertions fail in both snapshots.
- Final backend gate excluding only those nine baseline-confirmed failures: **1,355 passed, 9 deselected**, in 265.02 seconds. All test assertions remain unchanged. The exclusion expression was `not test_confidence_is_not_discovery_wall and not test_composite_determinism_60_observed_only_and_validator and not test_invalid_candidate_does_not_hide_valid_candidate and not test_copy_exact_new_saved_preferred_unowned_and_immutable`.
- Diff whitespace checks passed. No live provider/API-key smoke test was performed; connection tests used dummy keys and mocked transports.

The unchanged baseline failures are:

- `test_confidence_is_not_discovery_wall[1,4,14,15,20]` (five cases).
- `test_composite_determinism_60_observed_only_and_validator`.
- `test_invalid_candidate_does_not_hide_valid_candidate`.
- `test_copy_exact_new_saved_preferred_unowned_and_immutable[tournament,composite]` (two cases).

These fixtures include rotated card metadata and expect a valid composite/copy. Neither their assertions nor the legality/consensus behavior was changed in this settings task.

## PM retest

1. Open Settings → Agent Settings. Select one provider, paste its key and Test & Apply. Observe progress and connected status; Done closes the modal. A test can incur provider API charges.
2. Replace with a rejected key; confirm failure leaves the prior connection active. Replace with a valid key, restart the API and verify the saved provider is available.
3. Disconnect; restart and verify it stays disconnected even if the launcher supplies prior environment configuration.
4. Switch providers only after the current Agent request completes. Verify an existing conversation stays visible and the next request uses the applied provider.
5. Run the established Dragapult explanation/change/recount flow; then a fresh Pikachu, Gengar or Mega Lopunny custom build and the explicit Lopunny Dusknoir consensus path. Confirm exact-60/artifact behavior and consensus remain unchanged.
6. Exercise System, Light and Dark; reload and navigate between Library, Collection and Deck Builder. Confirm readable surfaces, unchanged artwork/finish effects and saved local mode.

No merge, tag, certification, Analytics activation or Phase 7D work was performed.
