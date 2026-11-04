# Changelog

All notable changes to HA Addon MCP Server will be documented in this file.

## [1.3.1] - 2026-11-04

### Fixed
- **Non-blocking Store Refresh (`reload_addons`)**: Supervisor add-on reload (`POST /addons/reload`) is inherently long-running (fetching external git repositories). `reload_addons` now uses a bounded wait (default 8s) and safely detaches long operations to an asynchronous background task (`asyncio.shield`), preventing client MCP timeouts (e.g. Paperclip/Claude 30s tool timeouts).
- **Tool Catalog Availability**: Fixed issue where slow or timed-out store refreshes hung the transport or caused subsequent tool calls and `tools/list` catalog requests to become unavailable.
- **ASGI Lifespan & SSE Reconnect Resilience**: Updated `routes.py` to return `AlreadySentResponse()` on SSE connections (fixing a `TypeError: 'NoneType' object is not callable` in Starlette on client disconnect) and handled client cancellations (`CancelledError`) cleanly across SSE and Streamable HTTP.
- **Client Timeouts in API Client**: Configured default `ClientTimeout` on `aiohttp.ClientSession` so supervisor requests never stall indefinitely.

## [1.3.0] - 2026-11-04

### Added
- **Streamable HTTP Transport (`/mcp` and `/mcp/{api_key}`)**: Modern single-endpoint HTTP transport for modern MCP clients (Cursor, Claude Desktop, Kiro) alongside SSE
- **Health Check Endpoint (`/health`)**: Lightweight unauthenticated ping endpoint returning server status and version
- **Lifeboat / Recovery Architecture**: Positioned as the dedicated recovery sidecar on port 8015, enabling AI assistants to inspect logs, restart, rebuild, or reconfigure other add-ons (including `ha_full_mcp`) if they crash or break during updates
- **Direct `/data/options.json` Parsing**: Reads configuration directly from Home Assistant's JSON options for fast and reliable startup

### Fixed
- **Dependency Pin**: Pinned `mcp[cli]>=1.30.0,<2` to prevent breaking changes from MCP SDK v2.x
- **Authentication Robustness**: Added whitespace stripping and case-insensitive `Bearer` prefix support

## [1.2.0] - 2026-02-14

### Changed
- Renamed addon to "HA Addon MCP Server" for consistency
- Cleaned up documentation and removed outdated files
- Updated all references to use new addon name

## [1.1.0] - 2026-02-14

### Added
- `restart_homeassistant` tool - Restart Home Assistant Core from MCP
- Total of 18 management tools now available

## [1.0.0] - 2026-02-14

### Added
- Custom icon for better UI identification
- Production-ready release with 17 addon management tools

## [0.9.0] - 2026-02-14

### Added
- `get_supervisor_logs` tool for debugging addon builds and installations

## [0.8.0] - 2026-02-14

### Added
- `list_store_addons` - Browse available addons with search/filter
- `reload_addons` - Refresh addon catalog
- `check_addon_availability` - Verify system compatibility

## [0.7.0] - 2026-02-14

### Added
- `install_addon` and `uninstall_addon` tools
- `get_addon_configuration`, `set_addon_configuration`, `validate_addon_configuration` tools
- `rebuild_addon` tool for local/custom addons

## [0.6.0] - 2026-02-13

### Changed
- Switched to standard MCP SSE transport for better compatibility
- Updated endpoint from `/mcp` to `/sse`

### Added
- 7 core addon management tools (list, info, start, stop, restart, logs, update)

## [0.1.0] - 2026-02-07

### Added
- Initial release with basic MCP server infrastructure
- Home Assistant API integration
- Multi-architecture support
