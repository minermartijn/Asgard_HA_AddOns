#!/usr/bin/with-contenv bashio
# ==============================================================================
# HA Addon MCP Server (Lifeboat)
# Runs the lightweight MCP server for addon management & recovery
# ==============================================================================

bashio::log.info "Starting HA Addon MCP Server (Lifeboat)..."

# Run the MCP server (reads /data/options.json directly)
cd /app
exec python3 -u src/server.py
