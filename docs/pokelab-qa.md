# PokéLab — Mike's certification checklist

Status: engineering QA candidate, **not PM-certified**. Live AI-provider validation is deliberately deferred to Mike. All testing so far was on the development Windows computer, not an independent clean Windows installation.

## Run the build

1. Open `PokeLab.exe`. No Python, terminal, MCP server, or Inspector is required.
2. First launch can take a few seconds while the executable unpacks and initializes its local profile. The shipped text database should show 3,345 TCGdex Standard-legal physical printings from a complete 23,736-record English catalog synchronized on September 23, 2026. These are dated provider flags; refresh when needed.
3. Card images load on demand. New images need internet; previously cached images can work offline. Missing provider artwork must not block text browsing.
4. Use **Refresh Limitless** to collect a recent sample. It is intentionally paced, may take several minutes, and stops on rate-limit instructions. Existing cached evidence remains usable. **Cancel refresh** stops further work after the current request/batch.

## Browser and collection

- Switch Gallery → List → Gallery.
- Choose Pokémon, Trainers, and Energy. Item must not appear as a peer category of Trainer.
- Search a card. Choose a finish in the quantity control, then use minus/quantity/plus.
- Close/reopen; the exact printing and selected finish's quantity must persist.
- Check All, Owned, and Unowned. Owned means total quantity across finishes is positive.
- Select Pokémon + Psychic + Dragon. Results must match either selected type.
- Add Owned. Results must also be owned. A Water-only card must not pass this combined filter.
- Clear filters and confirm the complete Standard browser returns.

## Analytics and drill-down

- Hover briefly (<2 seconds): no popup.
- Stay over a card for ~2 seconds: analytics popup opens.
- Move into the popup: it remains interactive. Leave card+popup: it closes after a short grace period.
- Check sample size, observed date range, excluded unresolved lists, usage, average copies, and up to five archetypes.
- Change 7/30/60/90 days and confirm all values and drill-down use the same period.
- Set a Current Format start date in Settings before choosing that period. The date is explicit, not inferred.
- Click an archetype. Inspect event, player, placing, date, source, and the readable decklist.
- A period with no data must say unavailable rather than fabricate percentages.
- Known engineering evidence: 24 public events cached in an isolated QA profile; 1,112 fully mapped lists and 315 excluded unresolved lists in the 30-day sample. Night Stretcher showed 919 inclusions and a 120-list Dragapult drill-down. This QA profile is not silently installed as your personal profile or advertised as full-metagame coverage.

## Agent / your live-provider test

1. Open Settings. Select Anthropic, enter your API key, and save. Use an API key with billing enabled; a chat subscription alone is not the API credential.
2. Select a card such as Night Stretcher after refreshing Limitless.
3. Open the Agent pane. Select the timeframe.
4. Click **Preview exact evidence sent to AI**. Confirm it includes one card and compact aggregates, not raw decklists, player names, ownership quantities, or an image library.
5. Ask: “What are people pairing with this, and is there anything interesting here?”
6. Confirm the response is grounded in the shown evidence, distinguishes observations from hypotheses, and does not change collection/decks/settings.
7. Test invalid credentials and offline failure. No secret should appear in the error. Delete the key in Settings when desired.

## Engineering validation and remaining gates

- Automated suite: 82 passing tests at this milestone; original snapshot/MCP coverage preserved.
- Public TCGdex and Limitless integrations were exercised with real data. The latter hit a rate limit and preserved its cache.
- Provider request construction and safe errors tested using mocks; no live paid-provider success is claimed.
- Before certification: Mike must validate the executable on a clean Windows 11 x64 system, visual layout/input behavior, long-session responsiveness, collection edge cases, live provider configuration, and source coverage expectations.
- The executable is an unsigned QA build. Public release, signing, and PM certification are not implied by automated test success.
