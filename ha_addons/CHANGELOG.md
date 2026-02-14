# Changelog

All notable changes to HA Addon MCP Server will be documented in this file.

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
