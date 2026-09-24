# PokéLab desktop architecture assessment

This is the minimum-change desktop reconciliation of the existing Python project. The desktop does not start or require an MCP server. The earlier V1 card-data work was present as uncommitted local changes and has been preserved.

1. **Reusable code:** `tcg_lab/card_db.py`, `sync_cards.py`, `cards.py`, `models.py`, `service.py`, and `store.py` provide the card cache, sync/parser, deterministic snapshot, and existing deck services. Preserve the seven tools and their tests.
2. **MCP boundary:** `tcg_lab/server.py` owns protocol registration only. Provider/service composition moved to `tcg_lab/engine.py`. The desktop imports the native engine and never imports the MCP adapter.
3. **Desktop architecture:** Qt widgets → `PokeLabEngine` / `Analytics` / read-only `SelectedCardAgent` → SQLite or explicit provider adapters. Network refreshes and AI calls run in worker threads; ordinary browsing is local and paginated.
4. **UI technology:** PySide6/Qt Widgets keeps Python as the implementation language, supports desktop controls, image/network caching, accessible native controls, and Windows packaging without a browser/server runtime. This is a functional QA shell for later PM/Figma refinement, not a visual-design lock-in.
5. **Schema:** Keep `cards`, `sets`, and source metadata. Add `functional_cards`, `printing_identity`, and `collection(printing_id, variant, quantity)`. Add `events`, `tournament_decks`, `tournament_cards`, and non-secret `app_settings`. No destructive migration of saved decks. Functional signatures group matching gameplay fields; names alone never imply equivalence. Wording differences remain conservatively separate until curated rules exist.
6. **TCGdex:** Reuse the full English sync and its conditional refresh/resume behavior. Desktop queries require source `standard=true` and physical `game=tcg`. The QA seed holds the complete synchronized catalog, not a sample. Source dates and incomplete-sync status are visible. TCGdex legality is evidence, not independent official certification; the source may contain mistakes or delayed updates.
7. **Limitless:** Use the documented Play! Limitless tournaments/details/standings endpoints, not HTML scraping or an embedded website. Import PTCG Standard events with final placings and no custom bans/rules. Match official set codes (including current `abbreviation.official`) and collector numbers locally. Aggregate only fully mapped 60-card lists; show excluded unresolved counts. Retain event/player/place/date/archetype/list/source for drill-down. Cache by event, replace transactionally, respect 429 waits, pace requests, and avoid re-fetching events cached within 24 hours. The UI refresh targets up to 25 events within 90 days; it is explicitly a sample, not every tournament.
8. **AI:** `AIProvider.answer(question, context)` is vendor-independent. The initial implementation uses Anthropic Messages with Haiku 4.5 and a configurable model identifier. The context is one selected card plus locally computed statistics/top pairings and source references; it is bounded to 16,000 characters, with a 2,000-character question and 700-token output cap. There are no model-invoked tools or writes. Keys are protected by Windows DPAPI and never put in settings or source control. Live provider certification is assigned to Mike, as requested.
9. **Windows package:** PyInstaller builds a Windows x64 one-file `PokeLab.exe`, with Python/Qt and a text-only card seed. The first launch creates a writable `%LOCALAPPDATA%\PokeLab` profile; executable resources remain read-only. Existing profiles are never replaced by the seed. Card art is fetched lazily using a replaceable image provider and a bounded 100 MB cache. Packaging validates that the seed contains only card tables, preventing accidental bundling of a user profile.
10. **Sequence:** Inspect/preserve V1 → native engine and schema → browser/collection/filter vertical slice → normalized competitive data → interactive dwell tooltip/drill-down → bounded read-only agent → package → deterministic/native tests → Mike QA. Card synchronization was already implemented, so it was reused instead of repeated. Actual Limitless evidence exposed and drove the official-set-code correction.
11. **Unknowns/blockers:** No implementation blocker remains for the build. A live paid-provider request requires Mike's own API key and is intentionally left for his QA. Current Format requires an explicit start date in Settings; the app does not guess whether that means rotation or a new-set format. No clean separate Windows machine is available here for certification.
12. **MVP risks:** TCGdex pool/legality completeness; unresolved printing equivalence; biased/incomplete Play! Limitless submissions; absence of official paper-event coverage from that API; provider billing/authentication; unsigned-executable distribution; and final usability on Mike's hardware. These are exposed in the UI/docs rather than replaced with invented data. Manual certification is still required.

## Module map

- `pokelab/engine.py`: browser query representation, Standard filtering, identities, ownership.
- `pokelab/analytics.py`: source adapter, normalization, aggregate statistics, drill-down.
- `pokelab/agent.py`: provider protocol, compact context, read-only agent.
- `pokelab/secrets.py`: Windows account-bound encryption; no plaintext fallback.
- `pokelab/images.py`: image-provider interface and TCGdex URL construction.
- `pokelab/paths.py`: seed installation and writable-profile paths.
- `pokelab/desktop.py`: desktop controls and user-directed actions.
- `pokelab/ui_support.py`: worker tasks, image loader, hover timers/popup.
- `pokelab/presentation.py`: readable card/deck text.
- `scripts/build_desktop.py`: reproducible Windows packaging.
- `tests/test_desktop_engine.py`, `test_desktop_ui.py`: native deterministic and interaction tests, alongside all prior tests.

## Analytics definitions

Usage = lists containing the functional card / fully mapped submitted lists in cached qualifying events during the selected period. Average copies is conditioned on inclusion. Top-archetype percentages are shares of the included lists, not usage within that archetype. Time boundaries are UTC and shared by statistics and drill-down. Zero sample is reported as unavailable, never 0% usage. Cached metadata records source dates; missing mappings are not silently treated as absence. A refresh of card identities also re-normalizes cached evidence.

## API references

- [TCGdex card schema](https://tcgdex.dev/reference/card) and [image sizes](https://tcgdex.dev/assets)
- [Play! Limitless API and authentication/rate limits](https://docs.limitlesstcg.com/developer)
- [Tournament endpoints](https://docs.limitlesstcg.com/developer/tournaments)
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages) and [model primer](https://platform.claude.com/docs/en/claude_api_primer)
- [Qt for Python](https://doc.qt.io/qtforpython-6/) and [deployment](https://doc.qt.io/qtforpython-6/deployment/)
