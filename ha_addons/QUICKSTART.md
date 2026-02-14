# Home Assistant MCP Server - Quick Reference

## What Has Been Built

A production-ready Home Assistant add-on that implements a Model Context Protocol (MCP) server with comprehensive management capabilities.

✅ **Core Infrastructure**
- MCP server using official Python SDK with SSE transport
- Standard MCP SSE (Server-Sent Events) for HTTP connections
- Full compatibility with standard MCP clients (Kiro, Claude Desktop, etc.)
- Multi-architecture support (aarch64, amd64, armhf, armv7, i386)
- Cloudflare-compatible authentication (API key in path)

✅ **Current Features (18 Tools)**
- **Addon Lifecycle**: List, info, start, stop, restart, logs, update
- **Installation**: Install, uninstall, rebuild (local addons)
- **Configuration**: Get config, set config, validate config
- **Discovery**: List store addons, reload catalog, check availability
- **System**: Get supervisor logs, restart Home Assistant Core

## File Structure

```
ha_addons/
├── config.yaml           # HA add-on manifest
├── Dockerfile           # Container definition
├── requirements.txt     # Python dependencies
├── run.sh              # Startup script
├── README.md           # User documentation
├── CHANGELOG.md        # Version history
├── ARCHITECTURE.md     # Technical design
├── src/
│   ├── server.py       # Main entry point
│   ├── ha_client.py    # Home Assistant API client
│   ├── mcp_handlers.py # MCP protocol handlers
│   └── tools/
│       └── addon_tools.py # 18 management tools
```

## Key Design Decisions

### 1. **Standard MCP SSE Transport**
Uses official `SseServerTransport` for bidirectional communication over HTTP, ensuring compatibility with all standard MCP clients.

### 2. **Security & Authentication**
- **API Key Required**: All requests must provide a valid API key.
- **Flexible Auth**: Supports Path parameter (recommended), Query parameter, or Headers.
- **Timing Safe**: Uses constant-time comparison for all security checks.

### 3. **Supervisor Integration**
Directly integrates with the Home Assistant Supervisor API to provide administrative control over the entire addon ecosystem.

## How to Use

### Install as HA Add-on
1. Copy the `ha_addons` folder to `/addons/ha_mcp_server/` on your HA instance.
2. Go to **Settings > Add-ons > Add-on Store**.
3. Click the menu (top right) and select **Check for updates**.
4. Find **Home Assistant KIRO MCP Server** in the "Local Add-ons" section.
5. Install, configure your `api_key`, and start.

### Connect from Kiro
Add to `.kiro/settings/mcp.json`:
```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://YOUR_HA_IP:8015/sse?api_key=YOUR_KEY",
      "transport": "sse"
    }
  }
}
```

## Available Tools (18)

| Category | Tools |
|----------|-------|
| **Basics** | `list_addons`, `get_addon_info`, `get_addon_logs` |
| **Control** | `start_addon`, `stop_addon`, `restart_addon`, `update_addon` |
| **Setup** | `install_addon`, `uninstall_addon`, `rebuild_addon` |
| **Config** | `get_addon_configuration`, `set_addon_configuration`, `validate_addon_configuration` |
| **Catalog** | `list_store_addons`, `reload_addons`, `check_addon_availability` |
| **System** | `get_supervisor_logs`, `restart_homeassistant` |

## Version
**Current**: 1.1.0 (Stable / Production Ready)
**Status**: 🟢 Fully Operational
