# Ally preview freeze and local setup verification — October 11, 2026

Starting branch: `phase7c5-concrete-deck-resolution`.
Starting HEAD: `6c354e9c414111328cf2622c3503581c04dbdb03`.
The actual project is at `C:/Users/Mike/Documents/Codex/2026-09-25/referenced-chatgpt-conversation-this-is-an/work/phase5`;
the chat workspace was a separate empty repository. All implementation and runtime
verification used an isolated local clone in the chat workspace.

The only starting tracked modification was `scripts/Start-Phase5-QA.ps1`.
Its SHA-256 before and after verification is
`BB800264286E41FB5C080A817D7136A69F1796C79568CABFD5548C6782B32356`.
It is excluded from staging and the preview tag. No product source, QA launcher,
collection, or provider implementation was edited.

## Freeze strategy

`pokelab-ally-preview-2026-10-11` targets the starting HEAD above. The regression
report committed at that HEAD (`pre-ally-final-regression-gate.md`) records 1,412
backend passes, 140 frontend passes, 52 browser/integration passes, successful
TypeScript/build checks, and no unexplained failures. This verifies the recorded
broad gate for that exact product state; it is not a claim that those broad suites
were rerun during setup work.

Setup/docs follow in a separate commit. The wrappers compose the same uvicorn and
Vite runtime and the existing database initializers; product files are unchanged.
Clone the branch including the setup commit to get the commands below. Checking
out the product tag alone intentionally yields the tested product before wrappers.
No merge, push, Phase 7D work, or new certification is performed.

## Ally commands and behavior

```powershell
.\setup.ps1
.\start.ps1
# Later:
.\stop.ps1
# Restart by running stop, then start.
```

Prerequisites: Windows, Python 3.11+, Node.js LTS 22.12+ or 24+, and npm.
Setup checks versions, creates `.venv`, installs `.[web]` and locked frontend
packages, prepares `data/` and `.cache/local-web/`, downloads cards through the
existing TCGdex synchronizer when needed, and initializes the existing gameplay,
collection, competitive, and deck schemas. Repeated setup reuses matching installed
dependencies and populated caches. Interrupted card sync resumes through setup.
Optional `-CardsDatabase` / `-CompetitiveDatabase` read-only SQLite backups import
caches only if their local target does not exist. Only a newly copied card cache's
legacy Qt collection table is removed, preventing import of someone else's ownership.
Existing local collection/deck files are never replaced. No `.env` or secret file is
created; startup supplies local database paths directly to child processes.

Start launches loopback uvicorn on 8001 and Vite on 5173, prepares indexes offline,
checks backend status, frontend response and proxied backend status, checks listeners,
prints the URL, and opens the default browser (optional `-NoBrowser`). A lock excludes
simultaneous starts; healthy recorded servers are reused. Partial servers are safely
stopped before launching replacements. PID creation time and checkout ownership are
checked before stopping; the Windows venv Python child is included in cleanup.
Unrelated occupied ports cause a clear failure and are not stopped. Readiness has a
60-second deadline with bounded HTTP calls; process stop has a 10-second deadline.
Logs remain in `.cache/local-web/`. The QA Restart path is never invoked.

Gemini is entered only in Settings → Agent Settings → Test & Apply. The existing
Windows encrypted storage is unchanged. Analytics remains Coming Soon. A fresh
competitive database is empty; the existing in-app Sync control fetches tournament
evidence when the user requests it.

## Executed verification

- Clean local clone of the starting product SHA; no user collection copied.
- Fresh `.venv` and package installation, `pip check`, npm lockfile installation: PASS.
- Card and competitive data copied through read-only SQLite backups; 23,736 cached
  cards; existing gameplay/format index and all local schema initialization: PASS.
- Second setup with `-Offline`: PASS; another rerun preserved deliberately populated
  disposable collection quantities and deck workspace records exactly.
- PowerShell parser and Python bytecode syntax checks: PASS.
- Windows PowerShell 5.1 setup/start/repeated-start/stop and PowerShell 7 startup: PASS.
- API and frontend `/api/v1/status`: `ready=true`, 23,736 cards, complete sync;
  frontend root HTTP 200; loopback 8001/5173 listening: PASS.
- Repeated start preserved PIDs; stopped frontend recovery relaunched healthy servers;
  stop removed both listeners; simulated frontend launch failure cleaned API children: PASS.
- Missing Node, missing Python, missing offline cache: concise expected failures.
- Unrelated listener on 8001: concise expected failure, listener preserved.
- `git diff --check`, explicit staged-file review, credential/private-config scan: PASS.
- Original launcher checksum unchanged. Source collection checksum unchanged:
  `B028078C4C4F236DDB475834FBA6ED9AA271E118963C4F1F856FEF7E16E3FD84`.
- Test servers were stopped after verification. Generated databases, environments,
  node modules, logs, and test probe files remain ignored and are not committed.

Changed files: `setup.ps1`, `start.ps1`, `stop.ps1`, `scripts/Local-Web.ps1`,
`scripts/bootstrap-web.py`, `README.md`, and this report.
Final intended tracked status: only the pre-existing QA launcher modification.

## Limits and handoff

No live provider calls, competitive sync, or card network sync were performed.
Network use was limited to dependency installation. The default fresh TCGdex
download delegates to the existing synchronizer and was not exercised online;
the verified bootstrap path uses existing caches. Browser auto-opening is present
but runtime verification used `-NoBrowser` to avoid disrupting the user's browser.
No live Gemini quality claim or new broad regression/certification claim is made.
The freeze tag and follow-up commit are local; remote distribution/publishing is
outside this request. Setup must be run in Ally's own clone. Current user's databases
were not changed, and no API key is needed for installation or startup verification.

READY TO HAND TO ALLY with the setup commit included and these verification limits.
