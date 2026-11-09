# Demonstration plan: recover Full MCP with Lifeboat

**Status:** Recording and screenshots are not yet available. This document is a reproducible demonstration plan, not evidence of a completed test.

## Goal

Show why a separate recovery MCP server is useful: when Full MCP is intentionally stopped in a **test installation**, Lifeboat can remain reachable and help restore service.

## Preparation

1. Use a non-critical Home Assistant OS/Supervised test installation, never a production system with safety-critical devices.
2. Install both add-ons using [the repository installation instructions](../README.md).
3. Confirm both endpoints work with **distinct dummy/test credentials** and a local test network. Use TLS if access crosses a trusted boundary.
4. Prepare a known-good Home Assistant backup and independent access to the Supervisor UI; verify the backup is accessible.
5. Remove private entity names, addresses, user data, internal URLs, and secrets from the recording environment.

## Suggested recording sequence (60–120 seconds)

1. **Problem:** Show Full MCP responding to a harmless read-only request (`list_entities` or `list_addons`).
2. **Controlled failure:** Stop only Full MCP through the test Home Assistant UI; explicitly label it an intentional demo.
3. **Failure recognition:** Show the same read-only request failing on the Full MCP connection.
4. **Fallback:** Connect to Lifeboat using its independent MCP endpoint and call `get_addon_info` / `get_addon_logs` for Full MCP.
5. **Recovery:** Use Lifeboat `start_addon` or `restart_addon` to restore Full MCP. Avoid destructive operations in the demonstration.
6. **Verification:** Confirm Full MCP responds to a read-only request after restart.
7. **Boundary:** Explain that this only covers a failing add-on, not a failed host, Supervisor, or network.

## Safety checks before publishing

- Never show the full MCP URL if it embeds an API key; redact URL paths, request headers, query strings, tokens and logs.
- Don't reveal real device identifiers, cameras, family information, or exact physical location.
- Be clear which steps were tested and which are illustrative.
- Publish the verified demo video link in [README.md](../README.md) when it exists. Do not use a simulated demonstration as proof of recovery.
