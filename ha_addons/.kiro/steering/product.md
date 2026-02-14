# Product Overview

This is a Home Assistant MCP (Model Context Protocol) server that runs as a Home Assistant add-on. It exposes Home Assistant's capabilities through a standardized MCP API, allowing external tools and IDEs (like Kiro, Claude Desktop, or other MCP clients) to programmatically interact with Home Assistant.

## Addon Identity

- **Name**: Home Assistant KIRO MCP Server ADDON
- **Slug**: `local_ha_mcp_server_addon_kiro`
- **Current Version**: 0.6.0
- **Port**: 8015 (default)

## Core Functionality

The server provides remote access to:
- Add-on management (list, start, stop, restart, update, logs)
- Home Assistant Core API access (entities, devices, services)
- Supervisor API access (system control, configuration)

## Key Features

- SSE (Server-Sent Events) transport over HTTP/HTTPS for remote access
- API key authentication with Cloudflare-compatible path-based auth
- 7 add-on management tools currently implemented
- Designed for incremental feature expansion

## Target Users

Developers and power users who want to:
- Automate Home Assistant management through AI assistants
- Control Home Assistant from external tools and IDEs
- Manage add-ons programmatically
- Access Home Assistant APIs through a standardized protocol

## Deployment

Runs as a Home Assistant add-on, accessible via HTTP on port 8015 (configurable).
