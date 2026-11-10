## HA Addon MCP Server (Lifeboat) 1.4.0 — initial tagged GitHub release

A **separate Home Assistant MCP app with 22 tools**, focused on Supervisor app maintenance and recovery. It is designed to remain accessible when the main Full MCP app has stopped or failed during an update, **provided that Home Assistant Supervisor, the host, the network and Lifeboat itself are still running**.

This is the first tagged GitHub Release for an **existing, already-versioned project**, not the first code release.

### Why an independent second server?
If an assistant relies only on Full MCP and then stops, updates or breaks that same service, it may lose the connection needed to troubleshoot it. Lifeboat runs as a **different app on port 8015**, so a client configured to use both endpoints can still attempt to inspect logs, restart or rebuild the primary app.

This is **not automatic failover**, and it cannot recover a broken host, unavailable Supervisor or network outage.

### All 22 tools
**App operations (18)**:
`list_addons`, `get_addon_info`, `start_addon`, `stop_addon`, `restart_addon`, `get_addon_logs`, `update_addon`, `install_addon`, `uninstall_addon`, `get_addon_configuration`, `set_addon_configuration`, `validate_addon_configuration`, `rebuild_addon`, `list_store_addons`, `reload_addons`, `check_addon_availability`, `get_supervisor_logs`, `restart_homeassistant`.

**Targeted backup and recovery (4)**:
`create_addon_backup`, `list_backups`, `get_backup_info`, `restore_addon_backup`.

### Changes in 1.4.0
- Create, inspect and restore targeted single-app backups.
- Validate app membership before attempting a restore; support encrypted backups with password checks.
- Redact password, token and API-key values from MCP tool-call logging.
- Add regression tests for backup/restore paths and tool routing.

### Installation
1. Add `https://github.com/minermartijn/Asgard_HA_AddOns` to your Home Assistant app repositories.
2. Install **HA Addon MCP Server (Lifeboat)** and configure its MCP API key.
3. Connect your MCP client to Lifeboat's own SSE/Streamable HTTP endpoint. Default port: **8015**.
4. For recovery resilience, configure **both** Full MCP and Lifeboat as **separate MCP connections** in your client and test a harmless read-only tool on each.

**Security and limitations:** Lifeboat still has high-privilege Supervisor operations. Use a trusted network/VPN or secured access gateway. Do not expose port 8015 directly to the public internet. Prefer header authentication and keep backups/independent manual recovery access. See [SECURITY.md](../../SECURITY.md) and [architecture](../ARCHITECTURE.md).

**Test status:** GitHub Actions regression checks passed at the time of this release. The maintainer reports both MCP apps working on their own installation. This does not represent third-party testing or a security audit.
