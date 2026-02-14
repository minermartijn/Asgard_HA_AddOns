# Project Structure

## Addon Identity

This addon is deployed as:
- **Slug**: `local_ha_mcp_server_addon_kiro`
- **Name**: Home Assistant KIRO MCP Server ADDON
- **Version**: 0.6.0 (defined in config.yaml)

When referencing this addon in Home Assistant API calls or logs, always use the slug `local_ha_mcp_server_addon_kiro`.

## Directory Layout

```
ha_mcp_server/
├── .kiro/
│   └── steering/              # AI assistant guidance documents
├── src/                       # Main source code
│   ├── __init__.py
│   ├── server.py             # MCP server entry point
│   ├── config.py             # Configuration loader
│   ├── ha_client.py          # Home Assistant API client
│   ├── mcp_handlers.py       # MCP protocol handlers
│   ├── routes.py             # HTTP route definitions
│   └── tools/                # MCP tool implementations
│       ├── __init__.py
│       └── addon_tools.py    # Add-on management tools
├── config.yaml               # Add-on manifest and schema
├── build.json                # Container build configuration
├── Dockerfile                # Container definition
├── requirements.txt          # Python dependencies
├── run.sh                    # Add-on startup script
├── generate_api_key.py       # API key generation utility
├── test_mcp_client.py        # MCP client test script
├── test_sse_connection.py    # SSE connection test script
└── docs/                     # Documentation
    ├── README.md             # User documentation
    ├── ARCHITECTURE.md       # Technical architecture
    ├── DEVELOPMENT.md        # Development guide
    ├── CHANGELOG.md          # Version history
    └── various other docs
```

## Key Files

### Core Server Files
- `src/server.py` - Main entry point, initializes MCP server with SSE or stdio transport
- `src/routes.py` - Starlette route handlers for SSE and message endpoints
- `src/mcp_handlers.py` - MCP protocol handlers (list_tools, call_tool, list_resources, read_resource)

### API Integration
- `src/ha_client.py` - Home Assistant API client with methods for Supervisor and Core APIs
- `src/tools/addon_tools.py` - Tool definitions and handlers for add-on management

### Configuration
- `config.yaml` - Home Assistant add-on manifest (ports, permissions, schema)
- `src/config.py` - Configuration loader (reads from environment and options)

### Deployment
- `Dockerfile` - Multi-arch container build
- `build.json` - Build configuration for Home Assistant add-on system
- `run.sh` - Startup script that launches the Python server

## Code Organization Patterns

### MCP Tool Structure
Tools are organized by domain:
- `src/tools/addon_tools.py` - Add-on management (7 tools)
- Future: `src/tools/entity_tools.py` - Entity management
- Future: `src/tools/device_tools.py` - Device management

Each tool module provides:
1. `get_*_tool_definitions()` - Returns list of Tool objects with schemas
2. `handle_*_tool()` - Async handler that executes tool logic

### Handler Pattern
MCP handlers in `src/mcp_handlers.py` follow this pattern:
```python
def create_*_handler(ha_client):
    async def handler(*args):
        # Implementation
    return handler
```

This allows dependency injection of the HA client.

### Route Pattern
Routes in `src/routes.py` are created as factory functions:
```python
def create_*_handler(sse, server, api_key, ...):
    async def handler(request):
        # Implementation
    return handler
```

## Authentication Flow

1. Client connects to `/sse` or `/sse/{api_key}`
2. Server validates API key from path, query param, or headers
3. SSE transport tells client to use `/messages/{api_key}` for messages
4. API key in path survives Cloudflare proxy (headers don't)

## API Client Architecture

`HomeAssistantClient` provides two API access modes:
- **Supervisor API**: Uses `SUPERVISOR_TOKEN` env var, accesses `http://supervisor/*`
- **Core API**: Uses long-lived token from config, accesses `http://supervisor/core/*`

Methods use `use_ha_token` parameter to switch between token types.

## Extension Points

### Adding New Tools
1. Create tool module in `src/tools/`
2. Implement `get_*_tool_definitions()` and `handle_*_tool()`
3. Import in `src/mcp_handlers.py`
4. Add to `create_list_tools_handler()` and `create_call_tool_handler()`

### Adding New Resources
1. Add resource definition in `create_list_resources_handler()`
2. Add handler logic in `create_read_resource_handler()`

### Adding New Routes
1. Create handler factory in `src/routes.py`
2. Add Route to Starlette app in `src/server.py`
