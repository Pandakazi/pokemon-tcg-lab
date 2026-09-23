# Release verification — 0.1.1

## Automated tests

35 tests passed on Windows with Python 3.12. Tests cover the existing seven tools, deck counts and legality limitations, version persistence/concurrent writes, real HTTP MCP requests, `/health`, the read-only check, launcher setup/repair, preserving settings, failed installation, occupied ports, already-running detection, malformed status files, and ZIP exclusions/line endings.

## Fresh ZIP installation

A clean archive was extracted into a new folder whose path contained spaces. It had no `.venv`, `.env`, cached installation state, or saved decks. The documented Windows command with the one-process execution-policy fallback was run under Windows PowerShell 5.1.26100.9444. The launcher discovered installed Python 3.13.15 through `py`.

Verified outcomes:

- Created `.venv`, downloaded/installed runtime dependencies and the project, and created `.env` automatically.
- Started the server and printed readiness only after its own `/health` endpoint answered.
- Port 8000 was occupied. The launcher used 8001, and the existing port owner was left running.
- `/health` reported version 0.1.1 and `/mcp` responded to a real MCP client.
- `pytest` was not installed in the fresh environment; ordinary startup and both checks succeeded without it.
- The beginner read-only check discovered all seven tools and retrieved Mimikyu.
- The full smoke test called all seven tools, validated a 60-card Bully Box demo, saved/read two versions, compared their exact changes, and analyzed the opening hand.
- Repeating the launcher did not reinstall healthy dependencies or start a duplicate. It reported the running address.
- Test processes were stopped after testing. Pre-existing processes and the original project's deck database were not modified by the clean-copy test.

This simulates a new user extracting the ZIP on an existing Windows host with Python installed; it is not a fresh Windows virtual machine or a test of Python's installer UI. No global package installation was used for the app.

## Distribution inspection

The ZIP builder includes only release source, tests, documentation, the two launchers, `.env.example`, and intentional card/deck samples. There is one `pokemon-tcg-lab/` top-level folder. No `.venv`, `.env`, saved-deck database, log, cache, temporary file, build output, or egg-info is included. ZIP CRC verification passed. PowerShell is packaged with CRLF; the Mac launcher uses LF and an executable permission bit. Commands contain normal underscores without Markdown escapes.

## Known limitations

- No Mac runtime was available. The Mac launcher was reviewed statically for built-in Bash compatibility, quoted paths, Python version detection, Python.org install locations, LF endings and Intel/Apple Silicon usage. Actual Mac execution, installer/Gatekeeper behavior, and architecture-specific dependency installation remain unverified.
- Python 3.11 and 3.14 were not runtime-tested. The declared supported range remains Python 3.11+ within Python 3.
- A port can be taken between checking and binding. The launcher reports the failed start and asks for a retry; it does not terminate another application.
- First installation, repair and changed requirements need internet access. Corporate package proxies, organization PowerShell policies and offline first installation were not end-to-end tested.
- ChatGPT connection guidance was checked against current official OpenAI documentation. No tunnel/account registration or end-to-end ChatGPT installation was performed.
- V0 remains a single-owner, loopback-only server without OAuth. The sample is a demo, and passing supported deck checks is not tournament certification. See README.md for validation scope.
