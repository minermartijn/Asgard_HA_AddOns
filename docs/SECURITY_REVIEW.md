# MCP security review notes

**Scope:** Lightweight source-level review performed on 2026-11-09. Not a penetration test, threat-model workshop, or independent security audit.

## Confirmed and fixed in Full MCP v1.11.1 source

- **Full MCP tool toggle bypass:** The tool list was filtered by `enabled_tools`, but the call handler did not recheck the configured allowlist. The fix passes the same allowlist to the handler and denies disabled tool calls before routing.
- **Sensitive argument logging:** Full MCP logged entire tool-call arguments. The fix logs tool names only, rather than potentially exposing passwords or tokens.
- **Regression coverage:** Unit tests verify disabled and allowed calls, an empty allowlist, list consistency, and that a test secret does not appear in handler logs.

**Deployment caution:** The fix is merged into the repository's Full MCP v1.11.1 source. Running Home Assistant installations must update/rebuild the add-on separately for it to take effect.

## Remaining hardening opportunities

| Area | Observed configuration | Follow-up |
| --- | --- | --- |
| Privileges | MCP add-ons request Supervisor admin role and `SYS_ADMIN` | Identify which API operations need these capabilities; remove unnecessary privileges only after testing. |
| Network exposure | Both MCP add-ons use host networking and default to `0.0.0.0` | Restrict network access and use a VPN or an authenticated gateway with TLS for remote clients. |
| URL credentials | Both transports support API keys in path/query parameters | Prefer headers when possible; redact access logs, rotate exposed keys and assess alternatives for proxies. |
| CORS | Wildcard origins are configured, while `/health` is intentionally unauthenticated | Review cross-origin trust boundaries and sensitive metadata exposure; do not assume CORS is authentication. |
| Key lifecycle | An auto-generated MCP API key is printed into add-on logs for setup | Consider protected one-time display and stronger rotation/expiry guidance; treat historical logs as sensitive. |
| Destructive actions | Admin tools can modify integrations, config, backups and add-ons | Require explicit human approval in the client and consider server-side operation-specific constraints. |
| Regression coverage | Tests cover several tools but not every privileged path | Add route-level auth tests, abuse tests, backup/restore integration tests and Home Assistant test-instance smoke checks. |

## Operational guidance

1. Keep real credentials out of source control and public demos. Use separate credentials for Full MCP and Lifeboat.
2. Keep an independent recovery path and verified backups.
3. Only rely on a new version after tests pass and it has been verified on a non-critical Home Assistant instance.
4. Report vulnerabilities privately according to [SECURITY.md](../SECURITY.md).

The repository's security policy provides deployment advice; it is not a warranty that every risk is mitigated.
