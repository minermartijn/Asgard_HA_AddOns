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

# Get Supervisor token (automatically provided by Home Assistant)
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"

bashio::log.info "Starting HA Addon MCP Server..."
bashio::log.info "Log Level: ${LOG_LEVEL}"
bashio::log.info "Listening on: ${HOST}:${PORT}"
bashio::log.info "API Key configured: $([ -n "${API_KEY}" ] && echo 'Yes' || echo 'No (will generate)')"

# Run the MCP server
cd /app
exec python3 -u src/server.py
