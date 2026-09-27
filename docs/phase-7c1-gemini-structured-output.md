# Gemini Research structured output

PM observed a Crispin response rejected at JSON parsing. Gemini Research now
requests structured output rather than relying on prompt wording alone.

The existing HTTP transport remains the Gemini OpenAI-compatible
`POST https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`.
Research supplies `Answer.model_json_schema()` through the optional
`response_schema` transport argument. Only Gemini emits
`response_format.type=json_schema`, with `json_schema.name=pokelab_research_answer`,
`strict=true`, and the generated schema. No SDK/API migration or model change.

The Pydantic schema is passed directly: no keywords removed/transformed, no
competing manual schema or compatibility projection. Definitions/references,
required fields, enum/constant values, additional-property restrictions and
structural bounds remain as generated. Remote acceptance is not established by
mock tests; no live request or network documentation lookup was performed.

Local validation remains authoritative, including strict JSON, schema, outcome
semantics, exact citation membership, whitespace checks and the 16,384-byte answer
ceiling. Semantic instructions and prompt examples are unchanged. The existing
assessment does not automatically prove citation entailment. Provider-side JSON
constraints do not establish truth or rules authority. There is no JSON repair,
retry, fallback, new logging or persistence. Qualification does not supply a schema;
other adapters ignore the optional parameter and retain identical request bodies.

Focused verification: 270 tests passed. One final network-blocked backend gate:
550 tests passed (two dependency deprecation warnings). `git diff --check` passed.
No frontend production changes; frontend/browser runs are unnecessary.
Frozen evidence/qualification records and the retained Budew hash are unchanged.

## PM retest (only after separate live authorization)

No environment-variable changes are required. Retain the existing server-side key,
explicit `gemini` / `gemini-3.5-flash-lite` configuration and all $0 gates.
From the existing configured PowerShell session:

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
.\scripts\Start-Phase5-QA.ps1 -Action Restart -SourceRepository 'C:\Users\Mike\Documents\pokemon-tcg-lab' -ApiPort 8003 -WebPort 5175 -PhaseLabel 'Phase 7C.1'
Invoke-RestMethod 'http://127.0.0.1:8003/api/v1/agent/status' | ConvertTo-Json -Depth 5
```

Check `available=true`, provider `gemini`, model `gemini-3.5-flash-lite` before Ask.
Open `http://127.0.0.1:5175`, retain the Dragapult deck/revision 157/30-day context,
select Crispin's exact printing/finish and choose Ask about this card. After PM
authorizes a live submission, submit once: `What would this deck lose if I removed
Crispin?` Do not submit a duplicate or retry. Review the answer/citations or, on
failure, expand Validation details and report only safe diagnostics. A restart or
status check alone does not authorize inference. This pass did neither.
