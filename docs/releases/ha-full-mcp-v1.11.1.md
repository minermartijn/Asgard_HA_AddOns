## HA Full MCP Server 1.11.1 — initial tagged GitHub release

An independently installable Home Assistant add-on exposing **62 configured Model Context Protocol tools** for MCP-compatible clients. The tool catalog covers add-ons and Supervisor operations, backups, integrations, entities, dashboards, automations, inventory, and diagnostics.

This is the first tagged GitHub Release for an **existing, already-versioned project**, not the first code release.

### Key capabilities
- **62 tools in 8 groups:** add-on/system (22), backup (5), integration (4), entity (6), registry inventory (3), dashboard (4), automation (8), and diagnostics (10).
- SSE and Streamable HTTP MCP transports, including bearer/API-key header authentication.
- Explicit per-tool enable/disable toggles in the add-on configuration.
- Home Assistant OS/Supervised add-on packaging, targeting `amd64` and `aarch64`.

### Changes in 1.11.1
- **Security:** Disabled tools are now denied at execution time (not merely hidden from MCP tool discovery).
- **Security:** Raw MCP tool arguments are no longer logged, reducing the risk of exposing credentials in application logs.
- Regression tests for enabled/disabled tool calls, empty allowlists, and secret redaction.

### From 1.11.0
- Added read-only area, device and config-entry inventory tools with optional filters.

### Installation
1. Add `https://github.com/minermartijn/Asgard_HA_AddOns` to your Home Assistant add-on repositories.
2. Install **HA Full MCP Server**, configure its token and MCP API key, and choose the enabled tools.
3. Connect your MCP-compatible client to the configured SSE or Streamable HTTP endpoint. Default port: **8010**.
4. Verify with a read-only tool before granting any state-changing actions to an AI assistant.

**Security and limitations:** This MCP server can modify critical Home Assistant configuration and add-ons. Treat both the MCP API key and the underlying Home Assistant token as administrative credentials. Do not expose port 8010 directly to the public internet; use a trusted network/VPN or a secured access gateway. Prefer header authentication over URL credentials, which can leak through logs. See [SECURITY.md](../../SECURITY.md) and [architecture](../ARCHITECTURE.md).

**Test status:** GitHub Actions syntax, manifest, and regression checks passed at the time of this release. The maintainer reports both MCP add-ons working on their own installation. This does not represent third-party testing or a security audit.
