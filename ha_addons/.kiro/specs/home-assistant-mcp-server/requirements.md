# Home Assistant MCP Server - Requirements

## Overview

A Model Context Protocol (MCP) server that runs as a Home Assistant add-on, providing programmatic access to Home Assistant's capabilities through a standardized API. The server enables external tools and IDEs (like Kiro, Claude Desktop, or other MCP clients) to interact with Home Assistant remotely.

## User Stories

### US-1: Remote Add-on Management
As a Home Assistant user, I want to manage my add-ons remotely through an MCP client so that I can control my Home Assistant installation from external tools.

**Acceptance Criteria:**
1. User can list all installed add-ons with their status
2. User can start, stop, and restart add-ons
3. User can view add-on logs
4. User can check for and install add-on updates
5. User can get detailed information about specific add-ons

### US-2: Secure Remote Access
As a Home Assistant administrator, I want secure authentication for the MCP server so that unauthorized users cannot access my Home Assistant instance.

**Acceptance Criteria:**
1. Server requires API key authentication for all requests
2. API key can be configured or auto-generated
3. Authentication works through Cloudflare proxies (path-based auth)
4. Unauthorized requests return 401 status
5. API key is logged on startup for user reference

### US-3: SSE Transport for Remote Connectivity
As a developer, I want to connect to the MCP server over HTTP using SSE transport so that I can access it remotely without direct network access.

**Acceptance Criteria:**
1. Server supports SSE (Server-Sent Events) transport
2. Server listens on configurable host and port (default: 0.0.0.0:8015)
3. SSE endpoint is accessible at `/sse`
4. Messages endpoint accepts POST requests at `/messages/{api_key}`
5. CORS is enabled for cross-origin requests

### US-4: Home Assistant Add-on Integration
As a Home Assistant user, I want to install the MCP server as a standard add-on so that it integrates seamlessly with my Home Assistant setup.

**Acceptance Criteria:**
1. Server runs as a Home Assistant add-on
2. Add-on has proper manifest (config.yaml) with permissions
3. Add-on can access Supervisor API using SUPERVISOR_TOKEN
4. Add-on can access Home Assistant Core API with long-lived token
5. Add-on supports multi-architecture (aarch64, amd64, armhf, armv7, i386)

### US-5: Configurable Server Settings
As a Home Assistant administrator, I want to configure the MCP server settings so that I can customize it for my environment.

**Acceptance Criteria:**
1. User can configure log level (debug, info, warning, error)
2. User can configure host and port
3. User can configure transport type (sse or stdio)
4. User can provide Home Assistant long-lived token
5. User can set custom API key
6. Configuration is validated on startup

### US-6: Comprehensive Logging
As a developer, I want detailed logs from the MCP server so that I can troubleshoot issues and monitor operations.

**Acceptance Criteria:**
1. Server logs all configuration on startup
2. Server logs authentication attempts (success and failure)
3. Server logs tool executions with arguments
4. Server logs API errors with details
5. Log level is configurable
6. Logs are accessible through Home Assistant add-on logs

### US-7: Clean Error Handling
As a user, I want the server to handle errors gracefully so that I get meaningful error messages instead of crashes.

**Acceptance Criteria:**
1. Invalid API keys return 401 with clear error message
2. Missing add-on slugs return descriptive errors
3. API failures are caught and logged
4. Network errors are handled gracefully
5. Server doesn't crash on tool execution errors

## Technical Requirements

### TR-1: MCP Protocol Compliance
- Server must implement MCP protocol version 1.0.0+
- Server must support list_tools, call_tool, list_resources, read_resource
- Server must use proper MCP types (Tool, TextContent, etc.)

### TR-2: Home Assistant API Integration
- Server must use Supervisor API for add-on management
- Server must support Home Assistant Core API for future entity management
- Server must use official Home Assistant API endpoints only
- Server must handle API authentication with Bearer tokens

### TR-3: Cloudflare Compatibility
- Server must embed API key in message endpoint path
- Server must work behind Cloudflare tunnels/proxies
- Server must not rely on headers that Cloudflare strips

### TR-4: Performance
- Server must respond to tool calls within 5 seconds (excluding long operations)
- Server must handle concurrent requests
- Server must not block on I/O operations (use async/await)

### TR-5: Security
- Server must validate all inputs
- Server must not expose sensitive tokens in responses
- Server must use HTTPS in production (via Cloudflare)
- Server must generate strong API keys (32+ bytes)

## Non-Functional Requirements

### NFR-1: Reliability
- Server must restart automatically on failure (via Home Assistant supervisor)
- Server must handle network interruptions gracefully
- Server must not lose state on reconnection

### NFR-2: Maintainability
- Code must follow Python best practices
- Code must be well-documented with docstrings
- Code must use type hints
- Code must be organized by domain (tools, routes, handlers)

### NFR-3: Extensibility
- New tools must be easy to add (modular tool structure)
- New resources must be easy to add
- New transports must be supportable (stdio already supported)

### NFR-4: Compatibility
- Server must work with all MCP clients (Kiro, Claude Desktop, etc.)
- Server must work on all Home Assistant supported architectures
- Server must work with Home Assistant Supervisor API

## Out of Scope

- Direct database access to Home Assistant
- Undocumented Home Assistant API usage
- Filesystem manipulation outside mapped directories
- Bypassing Home Assistant authentication
- Real-time streaming of entity states (future feature)
- WebSocket-based MCP transport (SSE only for now)

## Success Metrics

1. All 7 add-on management tools work correctly
2. Server works through Cloudflare proxy without errors
3. No TypeError or other exceptions in logs during normal operation
4. Authentication success rate > 99%
5. Tool execution success rate > 95%
6. Server uptime > 99.9%

## Dependencies

- Python 3.11+
- mcp[cli] >= 1.0.0
- uvicorn >= 0.30.0
- starlette >= 0.37.0
- sse-starlette >= 2.0.0
- aiohttp >= 3.9.0
- Home Assistant Supervisor
- Home Assistant Core (optional, for entity management)

## Constraints

- Must run within Home Assistant add-on environment
- Must use only officially supported Home Assistant APIs
- Must not require root privileges beyond what add-on provides
- Must work with limited resources (typical Home Assistant hardware)
