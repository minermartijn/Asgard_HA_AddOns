#!/usr/bin/with-contenv bashio
# ==============================================================================
# HA Addon MCP Server
# Runs the MCP server with proper configuration
# ==============================================================================

# Get options from add-on configuration
export LOG_LEVEL=$(bashio::config 'log_level')
export HOST=$(bashio::config 'host')
export PORT=$(bashio::config 'port')
export TRANSPORT=$(bashio::config 'transport')
export HA_TOKEN=$(bashio::config 'ha_token')
export API_KEY=$(bashio::config 'api_key')

# Export individual tool enable/disable flags
# Addon Information Tools
export TOOL_LIST_ADDONS=$(bashio::config 'tool_list_addons')
export TOOL_GET_ADDON_INFO=$(bashio::config 'tool_get_addon_info')
export TOOL_GET_ADDON_LOGS=$(bashio::config 'tool_get_addon_logs')

# Addon Control Tools
export TOOL_START_ADDON=$(bashio::config 'tool_start_addon')
export TOOL_STOP_ADDON=$(bashio::config 'tool_stop_addon')
export TOOL_RESTART_ADDON=$(bashio::config 'tool_restart_addon')

# Addon Management Tools
export TOOL_UPDATE_ADDON=$(bashio::config 'tool_update_addon')
export TOOL_INSTALL_ADDON=$(bashio::config 'tool_install_addon')
export TOOL_UNINSTALL_ADDON=$(bashio::config 'tool_uninstall_addon')

# Addon Configuration Tools
export TOOL_GET_ADDON_CONFIGURATION=$(bashio::config 'tool_get_addon_configuration')
export TOOL_SET_ADDON_CONFIGURATION=$(bashio::config 'tool_set_addon_configuration')
export TOOL_VALIDATE_ADDON_CONFIGURATION=$(bashio::config 'tool_validate_addon_configuration')

# Addon Advanced Tools
export TOOL_REBUILD_ADDON=$(bashio::config 'tool_rebuild_addon')
export TOOL_LIST_STORE_ADDONS=$(bashio::config 'tool_list_store_addons')
export TOOL_RELOAD_ADDONS=$(bashio::config 'tool_reload_addons')
export TOOL_CHECK_ADDON_AVAILABILITY=$(bashio::config 'tool_check_addon_availability')

# System Tools
export TOOL_GET_SUPERVISOR_LOGS=$(bashio::config 'tool_get_supervisor_logs')
export TOOL_RESTART_HOMEASSISTANT=$(bashio::config 'tool_restart_homeassistant')

# Get Supervisor token (automatically provided by Home Assistant)
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"

bashio::log.info "Starting HA Addon MCP Server..."
bashio::log.info "Log Level: ${LOG_LEVEL}"
bashio::log.info "Listening on: ${HOST}:${PORT}"
bashio::log.info "API Key configured: $([ -n "${API_KEY}" ] && echo 'Yes' || echo 'No (will generate)')"

# Run the MCP server
cd /app
exec python3 -u src/server.py
