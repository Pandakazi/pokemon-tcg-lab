> Historical optional MCP deployment guidance, not the web application's hosting plan. See [ADR 001](adr-001-web-first.md).

# Private connection and later public deployment

V0 is a single-owner local backend. Local HTTP and stdio work now; account registration, hosted authentication, public hosting, and directory submission are future steps.

## Private ChatGPT test

1. Start the server locally and run `scripts/smoke_test.py`.
2. Enable developer mode in ChatGPT if the account/workspace permits it.
3. Follow [OpenAI's private-server connection instructions](https://developers.openai.com/plugins/deploy/connect-chatgpt). Use Secure MCP Tunnel to reach `http://127.0.0.1:8000/mcp` without exposing it publicly. Tunnel setup is account-dependent and is not performed by this project.
4. Discover the tools. Check that `save_deck_version` is marked as a write tool; the other six are reads. Allow saving only when you intend to create a version.
5. Try “Get and analyze Bully Box (demo)”; compare two demo versions returned by the smoke test. Validate a deliberately short deck and verify the error is surfaced.

For a local stdio-capable MCP client, configure its command as the absolute path to this project's virtual-environment Python, arguments `-m tcg_lab.server --transport stdio`, and working directory as this project. Set `TCG_DB_PATH` to an absolute path when the client cannot set a working directory. No global client configuration has been changed.

## Public deployment path

Use `create_server()` in `tcg_lab.server` as the server factory; the SDK exposes `streamable_http_app()` for ASGI integration. Keep the existing loopback binding behind a same-host reverse proxy for a single-user deployment. Container/multi-host deployment needs explicit bind, host, and Origin allowlists; do not disable the SDK's DNS-rebinding protections to make a proxy work.

Before serving multiple users, add verified OAuth identities and scope every storage query and uniqueness constraint to an owner ID. The current shared SQLite store provides no user isolation. A public anonymous deployment would expose every saved deck to every caller and must not use this single-owner design unchanged.

Add authentication discovery/OAuth according to the [official authentication guide](https://developers.openai.com/plugins/build/auth), then stable HTTPS hosting, persistent storage/backups, request limits, monitoring, and sanitized logs. A small single-instance service can keep SQLite on a persistent volume; multi-instance deployment should use a shared transactional database.

Package the plugin after the server connection is registered, using the actual assigned connection identifier and the current [plugin packaging instructions](https://developers.openai.com/plugins/build/plugins). Do not invent a connection ID or reuse the obsolete ChatGPT `ai-plugin.json` format. Complete the current privacy, data-rights, support, and review requirements before submission.

OpenAI's [MCP server guide](https://developers.openai.com/plugins/build/mcp-server) requires a stable public HTTPS endpoint for public submission; a Secure MCP Tunnel alone, temporary tunnel, or local endpoint does not meet that requirement. Hosting and registration are intentionally not performed as part of this local milestone.

