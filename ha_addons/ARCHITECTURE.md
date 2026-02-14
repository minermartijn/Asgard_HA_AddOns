# Home Assistant MCP Server - Architecture & Design

## Overview

This add-on implements a Model Context Protocol (MCP) server that provides safe, documented access to Home Assistant's APIs, specifically focused on comprehensive add-on management and system control.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Client (Kiro, Claude)                │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (SSE Transport)
                         │ Port 8015
┌────────────────────────┴────────────────────────────────────┐
│              Home Assistant MCP Server Add-on                │
│                                                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │              MCP Server (Python)                    │   │
│  │  - SseServerTransport                               │   │
│  │  - Starlette Web Framework                          │   │
│  │  - Resource & Tool handlers (18 tools)              │   │
│  └──────┬──────────────────────────┬───────────────────┘   │
│         │                          │                         │
│  ┌──────┴──────────┐      ┌───────┴────────────┐          │
│  │  HA WebSocket   │      │  Supervisor API    │          │
│  │  Client         │      │  Client (REST)     │          │
│  └──────┬──────────┘      └───────┬────────────┘          │
└─────────┼─────────────────────────┼───────────────────────┘
          │                         │
          │ WS API (Port 8123)      │ Supervisor Socket
          │                         │
┌─────────┴─────────────────────────┴───────────────────────┐
│              Home Assistant Supervisor                      │
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  Home Assistant  │      │  Add-on Manager  │           │
│  │  Core            │      │                  │           │
│  └──────────────────┘      └──────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## API Access Strategy

### Home Assistant Core
- **WebSocket API**: Interface for real-time entity/state management (Infrastructure in place).
- **REST API**: Used for core system controls like `restart_homeassistant`.

### Supervisor
- **Supervisor API**: Primary interface for add-on lifecycle, logs, and store management.
- **Authentication**: Uses the internal `SUPERVISOR_TOKEN` automatically provided to add-ons.

## Security Model

### Authentication
- **API Key**: A 256-bit secure key is required for all connections.
- **Path-based Auth**: Support for `.../sse/{api_key}` ensures compatibility with Cloudflare and other proxies that might strip headers.
- **Timing Safe**: All key comparisons use constant-time algorithms to prevent side-channel attacks.

### Permissions (config.yaml)
- `homeassistant_api: true`
- `hassio_api: true`
- `supervisor_api: true`
- `privileged: [SYS_ADMIN]` (for advanced supervisor operations)

## Implementation Status

### Phase 1: Core Infrastructure ✅
- MCP server setup with Python SDK.
- Standard SSE transport implementation.
- API Key authentication.

### Phase 2: Add-on Lifecycle ✅
- `list_addons`, `get_addon_info`, `start_addon`, `stop_addon`, `restart_addon`.

### Phase 3: Advanced Management ✅
- `get_addon_logs`, `update_addon` (with status monitoring).
- `install_addon`, `uninstall_addon`, `rebuild_addon`.

### Phase 4: Configuration & Validation ✅
- `get_addon_configuration`, `set_addon_configuration`, `validate_addon_configuration`.

### Phase 5: Discovery & System ✅
- `list_store_addons`, `reload_addons`, `check_addon_availability`.
- `get_supervisor_logs`, `restart_homeassistant`.

### Phase 6: Entity Management (Future) ⏳
- Planned expansion to include entity states, service calls, and ghost entity detection.

## MCP Tools (18)

The server currently implements 18 specialized tools for Home Assistant management:

1.  **Management**: `list_addons`, `get_addon_info`, `start_addon`, `stop_addon`, `restart_addon`, `update_addon`.
2.  **Maintenance**: `install_addon`, `uninstall_addon`, `rebuild_addon`.
3.  **Config**: `get_addon_configuration`, `set_addon_configuration`, `validate_addon_configuration`.
4.  **Discovery**: `list_store_addons`, `reload_addons`, `check_addon_availability`.
5.  **System**: `get_supervisor_logs`, `restart_homeassistant`.

## Design Principles

1.  **Safety First**: Destructive operations (uninstall, restart) provide detailed warnings and status updates.
2.  **Standard Compliance**: Strictly follows the Model Context Protocol specification.
3.  **Proxy Friendly**: Designed to work behind Nginx, Cloudflare, and Home Assistant Ingress (future).
4.  **Informative**: Responses are formatted in Markdown to provide clear, actionable information to the LLM and user.

## Limitations

- **Direct Database**: No direct access to SQLite/Recorder database (uses APIs only).
- **Filesystem**: Access limited to mapped directories (`/config`, `/ssl`, `/addons`, `/backup`).
- **Ingress**: MCP currently requires a direct port (8015) as standard SSE doesn't always play nice with the double-proxy of HA Ingress without custom headers.
