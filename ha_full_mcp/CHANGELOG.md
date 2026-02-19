# Changelog

All notable changes to HA Full MCP Server will be documented in this file.

## [1.8.0] - 2026-02-19

### Changed
- **⚠️ BREAKING CHANGE: Configuration Structure Reorganized**
  - Tool toggles now organized into 11 collapsible sections in the UI
  - Environment variable names changed from `TOOL_*` to `SECTION_TOOL_NAME` format
  - Example: `TOOL_LIST_ADDONS` → `ADDON_INFORMATION_LIST_ADDONS`
  - Existing configurations will reset to defaults (all tools enabled)
  - Users must reconfigure tool toggles after updating

### Added
- **UI Sections for Better Organization**:
  - Addon Information (3 tools)
  - Addon Control (3 tools)
  - Addon Management (3 tools)
  - Addon Configuration (3 tools)
  - Addon Advanced (4 tools)
  - System Tools (6 tools)
  - Backup Tools (5 tools)
  - Integration Tools (4 tools)
  - Entity Tools (6 tools)
  - Dashboard Tools (4 tools)
  - Diagnostic Tools (10 tools)
- Professional, collapsible sections in Home Assistant configuration UI
- Improved user experience with logical tool grouping

### Technical
- Updated `config.yaml` to use nested dictionary structure for sections
- Updated `src/config.py` to read new environment variable format
- All 59 tools remain functional with new structure
- Tool toggle functionality verified and working correctly

### Migration Guide
1. Update the addon to version 1.8.0
2. All tools will be enabled by default
3. Review the new sectioned configuration UI
4. Disable any tools you don't want to use
5. Save and restart the addon

## [1.7.1] - 2026-02-16

### Added
- **Automation Management Tools (8 new tools)**:
  - `list_automations`: List all automations with status, triggers, and actions
  - `get_automation`: View detailed automation configuration
  - `create_automation`: Create new automations with triggers, conditions, and actions
  - `update_automation`: Modify existing automation configurations
  - `delete_automation`: Remove automations permanently
  - `enable_automation`: Enable disabled automations
  - `disable_automation`: Disable automations without deleting them
  - `trigger_automation`: Manually trigger automations for testing
- Full CRUD operations for automation management
- Support for all automation modes (single, restart, queued, parallel)
- Automation testing capabilities with condition skipping

### Changed
- Increased total tools from 41 to 49 (added 8 automation tools)
- Updated addon description to include automation management capabilities

### Fixed
- **Boolean Configuration Logic**: Fixed tool toggle handling to properly recognize false/0/no/off values
  - Previously, setting toggles to false in UI didn't disable tools after reboot
  - Now explicitly checks for false/0/no/off strings and disables tools correctly
  - Maintains backwards compatibility with true/1/yes values

### Technical
- Added `src/api/automation_api.py` (213 lines) - Automation API methods using WebSocket
- Added `src/tools/automation_tools.py` (398 lines) - Automation tool handlers
- Updated `src/api/__init__.py` to include AutomationAPI mixin
- Updated `src/mcp_handlers.py` with automation tool routing
- Updated `src/config.py` with automation tool configuration mappings and boolean fix
- All new files comply with 500-line guideline

## [1.5.0] - 2026-02-15

### Added
- **Dashboard Management Tools (4 new tools)**:
  - `list_dashboards`: List all available Lovelace dashboards
  - `get_dashboard_config`: View dashboard configuration and structure
  - `create_dashboard`: Create or update dashboards with views and cards
  - `delete_dashboard`: Remove custom dashboards
- Dashboard tools work with UI-managed dashboards (not just YAML mode)
- Full CRUD operations for dashboard management
- Support for multi-view dashboards with custom cards

### Changed
- Increased total tools from 37 to 41 (added 4 dashboard tools)
- Updated addon description to include dashboard management capabilities

### Technical
- Added `src/api/dashboard_api.py` (88 lines) - Dashboard API methods
- Added `src/tools/dashboard_tools.py` (217 lines) - Dashboard tool handlers
- Updated `src/api/__init__.py` to include DashboardAPI mixin
- Updated `src/mcp_handlers.py` with dashboard tool routing
- Updated `src/config.py` with dashboard tool configuration mappings
- All new files comply with 500-line guideline

## [1.4.2] - 2026-02-15

### Changed
- **Major Code Refactoring**: Improved codebase maintainability and AI-friendliness
  - Refactored `src/tools/addon_tools.py` (2,005 lines) into 9 focused modules
  - All Python files now under 500 lines for better readability and maintenance
  - Created `src/tools/addon/` directory with organized handler modules:
    - `definitions.py` (323 lines) - Tool schemas
    - `basic_handlers.py` (64 lines) - List and info tools
    - `lifecycle_handlers.py` (156 lines) - Start, stop, restart, logs, update
    - `addon_config_handlers.py` (351 lines) - Addon configuration management
    - `management_handlers.py` (432 lines) - Install and uninstall
    - `store_handlers.py` (379 lines) - Store browsing and addon availability
    - `logs_handlers.py` (266 lines) - System logs and HA restart
    - `config_file_handlers.py` (342 lines) - Configuration file operations
  - Updated imports in `src/mcp_handlers.py` to use new modular structure
  - No functional changes - all 37 tools work exactly as before

### Technical
- Better code organization with clear separation of concerns
- Easier to maintain and extend with new features
- Improved AI assistant compatibility for code editing
- Faster file operations and reduced merge conflicts

## [1.4.1] - 2026-02-15

### Fixed
- **Integration Tools API Access**: Changed Core API URL from `http://supervisor/core` to `http://homeassistant:8123`
  - Fixed 401 Unauthorized errors when accessing entity states and services
  - Integration tools now work correctly with ha_token authentication
  - All 4 integration tools tested and working
- **Integration Management Implementation**: Updated to use domain-based approach
  - `list_integrations` now successfully lists all entity domains
  - `get_integration_info` shows entity count per domain
  - `reload_integration` calls domain reload services
  - `remove_integration` notes WebSocket API requirement for actual removal

### Tested
- ✅ All 5 backup tools fully tested and working
- ✅ All 4 integration tools tested and working (with REST API limitations noted)
- ✅ All 6 entity tools implemented and ready for testing

## [1.4.0] - 2026-02-15

### Added
- **Backup Management Tools (5 new tools)**:
  - `create_backup`: Create full or partial backups with optional encryption
  - `list_backups`: View all available backups with details
  - `get_backup_info`: Get detailed information about specific backups
  - `restore_backup`: Restore from full or partial backups
  - `delete_backup`: Remove old backups to free storage space

- **Integration Management Tools (4 new tools)**:
  - `list_integrations`: View all configured integrations with status
  - `reload_integration`: Reload integrations without restarting HA
  - `get_integration_info`: Get detailed integration information
  - `remove_integration`: Remove/delete integrations

- **Entity Management Tools (6 new tools)**:
  - `list_entities`: List all entities with domain/area filtering
  - `get_entity_state`: Get current state and attributes of entities
  - `set_entity_state`: Set entity states directly
  - `call_service`: Call any Home Assistant service to control devices
  - `get_services`: Discover all available services
  - `get_entity_history`: View historical state changes

### Changed
- Increased total tools from 22 to 37 (added 15 new tools)
- Updated addon description to reflect full Home Assistant management capabilities
- Enhanced README with entity control examples and use cases
- Improved configuration documentation for new tool categories

### Technical
- Added `backup_tools.py`, `integration_tools.py`, and `entity_tools.py` modules
- Extended `ha_client.py` with 15 new API methods for backup, integration, and entity management
- Updated `mcp_handlers.py` to route new tool categories
- Enhanced `config.py` with new tool environment variable mappings
- All new tools default to enabled (true) in configuration

## [1.3.5] - 2026-02-15

### Added
- **check_config tool**: Validate Home Assistant configuration before restarting
  - Checks configuration.yaml and all included files for errors
  - Prevents breaking changes by validating before restart
  - Provides clear feedback on validation status
  - Lists specific errors when validation fails
- Added PyYAML dependency for YAML validation in write_config_file

### Fixed
- Fixed YAML import error in write_config_file tool
- Improved error handling for configuration validation

## [1.3.4] - 2026-02-15

### Added
- **check_config tool** (initial implementation)

## [1.3.3] - 2026-02-15

### Added
- **get_homeassistant_logs tool**: Retrieve Home Assistant Core logs
  - Analyzes logs for errors, warnings, and automation activity
  - Shows component/integration loading status
  - Tracks automation and script execution
  - Provides helpful usage tips
- **read_config_file tool**: Read configuration files from /config directory
- **write_config_file tool**: Write configuration files with automatic backup
  - Creates timestamped backups before writing
  - Validates YAML syntax before writing
  - Provides safety tips and next steps

### Changed
- Increased total tools from 18 to 22 (added 4 new tools)

## [1.3.0] - 2026-02-14

### Added
- **Individual Tool Toggles**: Each of the 18 MCP tools now has its own enable/disable toggle
  - Appears as toggle switches in Home Assistant UI
  - Organized into 6 logical categories (Information, Control, Management, Configuration, Advanced, System)
  - All tools enabled by default - simply toggle off what you don't want
  - Perfect for security hardening, simplified interfaces, and custom configurations
- UI configuration guide showing how toggles appear in Home Assistant
- Tool customization guide with detailed use cases
- Configuration examples for common scenarios

### Changed
- Renamed addon to "HA Full MCP Server" (from "HA Addon MCP Server")
- Updated slug to `ha_full_mcp_server` (from `ha_addon_mcp_server`)
- Changed default port from 8015 to 8010
- Replaced list-based tool selection with individual boolean toggles
- Enhanced configuration schema with organized tool categories
- Improved logging to show enabled/disabled tool counts

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
