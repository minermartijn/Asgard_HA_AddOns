# Changelog

All notable changes to this Home Assistant add-on will be documented in this file.

## [1.1.0] - 2026-02-14

### Added
- **Restart Home Assistant Tool**:
  - `restart_homeassistant` - Restart Home Assistant Core from the MCP interface
  - Useful after configuration changes or integration updates
  - Provides clear warnings and expectations about the restart process
  - Includes monitoring guidance and usage recommendations
- Total of 18 management tools now available

### Improved
- Enhanced system control capabilities
- Better workflow for configuration changes requiring restart

## [1.0.0] - 2026-02-14 🎉

### Added
- **Custom Icon**: Added custom icon.png for better visual identification in Home Assistant UI
- **Production Ready**: First stable release with complete feature set

### Changed
- Version bumped to 1.0.0 to reflect production-ready status
- All 17 addon management tools fully tested and operational

### Summary
This release marks the completion of the Home Assistant KIRO MCP Server with comprehensive addon lifecycle management. The server now provides complete control over Home Assistant addons through a standardized MCP interface with 17 fully functional tools.

## [0.9.0] - 2026-02-14

### Added
- **Supervisor Logs Tool**:
  - `get_supervisor_logs` - Access Home Assistant Supervisor logs for debugging addon builds, installations, and system-level issues
  - Automatic log analysis highlighting errors, warnings, and addon activity
  - Truncation and formatting for readability
  - Essential for troubleshooting addon build failures
- Total of 17 addon management tools now available

### Improved
- Enhanced debugging capabilities for addon development
- Better visibility into supervisor operations
- Comprehensive log analysis with pattern detection

## [0.8.0] - 2026-02-14

### Added
- **3 New Addon Discovery & Management Tools**:
  - `list_store_addons` - Browse all available addons from the Home Assistant store with optional filtering by repository or search query
  - `reload_addons` - Refresh the addon catalog without restarting Home Assistant
  - `check_addon_availability` - Verify if an addon is compatible with your system architecture before installation
- Total of 16 addon management tools now available
- Repository filtering for store addon listings
- Search functionality for finding specific addons
- Architecture compatibility checking
- Detailed availability explanations when addons cannot be installed

### Improved
- Enhanced addon discovery workflow
- Better error messages for incompatible addons
- Comprehensive system architecture information in availability checks
- Tool routing updated to include all 16 tools

## [0.7.0] - 2026-02-14

### Added
- **6 New Addon Management Tools** - Complete addon lifecycle management:
  - `install_addon` - Install addons from the Home Assistant store
  - `uninstall_addon` - Remove addons with optional config preservation
  - `get_addon_configuration` - View current addon configuration and schema
  - `set_addon_configuration` - Update addon settings with validation
  - `validate_addon_configuration` - Test configuration before applying
  - `rebuild_addon` - Rebuild local/custom addons from source
- Total of 13 addon management tools now available
- Comprehensive error handling and user-friendly output for all new tools
- Detailed validation feedback and troubleshooting suggestions
- Configuration change tracking (before/after comparison)

### Improved
- Enhanced tool routing in MCP handlers to include all 13 tools
- Better error messages with actionable suggestions
- Async job tracking for install/uninstall/rebuild operations
- Automatic addon state verification after operations

## [0.6.0] - 2026-02-13

### Changed
- **BREAKING**: Switched from custom JSON-RPC to standard MCP SSE (Server-Sent Events) transport
- Updated endpoint from `/mcp` to `/sse` for standard MCP compatibility
- Now compatible with all standard MCP clients (Kiro, Claude Desktop, Cline, etc.)

### Added
- SSE transport support for HTTP-based MCP connections
- stdio transport option for process-based communication
- Comprehensive Kiro setup guide (KIRO_SETUP.md)
- Transport configuration option in addon settings
- Full addon management tools:
  - list_addons
  - get_addon_info
  - start_addon
  - stop_addon
  - restart_addon
  - get_addon_logs
  - update_addon (with automatic update checking and log monitoring)

### Fixed
- MCP client compatibility issues
- Tool routing and execution
- Proper MCP protocol implementation

### Migration Guide
If upgrading from v0.5.x:
1. Update addon to v0.6.0
2. Change transport setting from "streamable-http" to "sse"
3. Update MCP client configuration to use `/sse` endpoint instead of `/mcp`
4. Restart the addon

## [0.1.0] - 2026-02-07

### Added
- Initial release with basic MCP server infrastructure
- Streamable HTTP transport support (stateless, JSON responses)
- Home Assistant API connection framework
- Supervisor API connection framework
- Basic server info and config status resources
- Add-on configuration options (log_level, host, port)

### Architecture
- Python-based MCP server using official `mcp` SDK
- Lifespan management for API connections
- Docker-based deployment as Home Assistant add-on
- Support for multiple architectures (aarch64, amd64, armhf, armv7, i386)

### Permissions
- homeassistant_api: true
- hassio_api: true
- supervisor_api: true
- Mapped directories: config (rw), ssl (ro), addons (ro), backup (ro)

### Coming Soon
- Entity management tools
- Device management tools
- Ghost entity detection and removal
- System restart capabilities
