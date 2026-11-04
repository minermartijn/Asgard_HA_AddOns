#!/usr/bin/with-contenv bashio
# ==============================================================================
# HA Full MCP Server
# Runs the MCP server with proper configuration
# ==============================================================================

bashio::log.info "Starting HA Full MCP Server..."

# Run the MCP server (reads /data/options.json directly)
cd /app
exec python3 -u src/server.py
