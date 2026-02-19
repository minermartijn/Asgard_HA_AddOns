---
inclusion: always
---

# Home Assistant MCP Server Development Guide

This steering file provides comprehensive context for working with the Home Assistant MCP Server codebase. Use this as a reference when making changes or adding new features.

## Project Overview

**Purpose**: Provide an MCP (Model Context Protocol) server that allows AI assistants to manage and control Home Assistant through a standardized API.

**Current Version**: 1.6.0  
**Total Tools**: 49 (Addon: 22, Backup: 5, Integration: 4, Entity: 6, Dashboard: 4, Automation: 8)

## Architecture

### Core Components

1. **src/server.py** - Main entry point, starts the MCP server
2. **src/config.py** - Configuration management and tool toggles
3. **src/ha_client.py** - Home Assistant API client (imports from api/)
4. **src/api/** - API client modules (refactored for maintainability)
   - **base_client.py** - Authentication and HTTP request handling
   - **addon_api.py** - Addon management methods (mixin)
   - **system_api.py** - System operations (logs, config, restart) (mixin)
   - **backup_api.py** - Backup management methods (mixin)
   - **integration_api.py** - Integration management methods (mixin)
   - **entity_api.py** - Entity and service methods (mixin)
5. **src/mcp_handlers.py** - MCP protocol handlers (routes tool calls)
6. **src/routes.py** - HTTP/SSE transport layer
7. **src/auth.py** - API key authentication
8. **src/tools/** - Tool definitions and handlers

### Tool Organization

Tools are organized into separate modules by category:

**Addon Tools** (22 tools) - Organized in `src/tools/addon/`:
- **definitions.py** (323 lines) - All 22 addon tool schemas
- **basic_handlers.py** (64 lines) - list_addons, get_addon_info
- **lifecycle_handlers.py** (156 lines) - start, stop, restart, logs, update
- **addon_config_handlers.py** (351 lines) - get/set/validate addon configuration
- **management_handlers.py** (432 lines) - install, uninstall addons
- **store_handlers.py** (379 lines) - list_store, reload, check_availability, rebuild
- **logs_handlers.py** (266 lines) - supervisor/HA logs, restart HA
- **config_file_handlers.py** (342 lines) - read/write/check config files
- **__init__.py** (68 lines) - Router that dispatches to appropriate handlers

**Other Tool Modules**:
- **backup_tools.py** (371 lines) - 5 backup tools
- **integration_tools.py** (257 lines) - 4 integration tools
- **entity_tools.py** (425 lines) - 6 entity tools
- **dashboard_tools.py** (~300 lines) - 4 dashboard tools
- **automation_tools.py** (~400 lines) - 8 automation tools

### API Architecture

The `ha_client.py` uses two different APIs:

1. **Supervisor API** (`http://supervisor`) - For addon/system management
   - Uses `SUPERVISOR_TOKEN` environment variable
   - Endpoints: `/addons`, `/backups`, `/supervisor`, etc.
   - Authentication: `use_ha_token=False`

2. **Home Assistant Core API** (`http://homeassistant:8123`) - For entities/integrations
   - Uses `ha_token` from addon configuration (long-lived access token)
   - Endpoints: `/api/states`, `/api/services`, etc.
   - Authentication: `use_ha_token=True`
   - Note: Integration config entry management requires WebSocket API (not yet implemented)

## Adding New Tools

### Step-by-Step Process

When adding new tools, follow this exact pattern to ensure everything is integrated:

#### 1. Create Tool Definition

In the appropriate `src/tools/*_tools.py` file:

```python
def get_*_tool_definitions() -> list[Tool]:
    """Return all *-related tool definitions."""
    return [
        Tool(
            name="tool_name",
            description="Clear description of what the tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param_name": {
                        "type": "string",
                        "description": "Parameter description",
                    },
                },
                "required": ["param_name"],
            },
        ),
    ]
```

#### 2. Create Tool Handler

In the same file:

```python
async def handle_*_tool(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle * tool execution."""
    try:
        if name == "tool_name":
            # Extract arguments
            param = arguments.get("param_name")
            
            # Build result string
            result = "# Tool Output\n\n"
            
            # Call API method
            data = await ha_client.api_method(param)
            
            # Format output
            result += f"Result: {data}\n"
            
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
```

#### 3. Add API Method

In `src/ha_client.py`:

```python
async def api_method(self, param: str) -> dict[str, Any]:
    """API method description.
    
    Args:
        param: Parameter description
    
    Returns:
        Dictionary containing result data
    
    Raises:
        ValueError: If validation fails
        PermissionError: If insufficient permissions
        aiohttp.ClientError: If API request fails
    """
    # Validate input
    if not param:
        raise ValueError("param cannot be empty")
    
    try:
        # Make API request
        result = await self._make_request(
            "GET",  # or POST, DELETE, etc.
            f"{self.hassio_url}/endpoint/{param}",  # or self.ha_url for Core API
            use_ha_token=False  # True for Core API, False for Supervisor API
        )
        
        logger.info(f"API method completed: {param}")
        return result.get("data", {})
        
    except aiohttp.ClientResponseError as e:
        if e.status == 404:
            raise ValueError(f"Not found: {param}") from e
        elif e.status == 403:
            raise PermissionError(f"Insufficient permissions") from e
        else:
            logger.error(f"API error: HTTP {e.status}")
            raise
    except aiohttp.ClientError as e:
        logger.error(f"API request failed: {e}")
        raise
```

#### 4. Register in MCP Handlers

In `src/mcp_handlers.py`:

```python
# Import the new tool module
from tools.new_tools import get_new_tool_definitions, handle_new_tool

# In create_list_tools_handler:
all_tools_list.extend(get_new_tool_definitions())

# In create_call_tool_handler:
new_tools = ["tool_name", "another_tool"]

if name in new_tools:
    return await handle_new_tool(name, arguments, ha_client)
```

#### 5. Add Configuration Mapping

In `src/config.py`:

```python
all_tools = {
    # ... existing tools ...
    # New Tool Category
    "tool_name": "TOOL_TOOL_NAME",
    "another_tool": "TOOL_ANOTHER_TOOL",
}
```

#### 6. Update Addon Configuration

In `config.yaml`:

```yaml
version: "1.X.0"  # Increment version

options:
  # ... existing options ...
  # New Tool Category
  tool_tool_name: true
  tool_another_tool: true

schema:
  # ... existing schema ...
  # New Tool Category
  tool_tool_name: bool?
  tool_another_tool: bool?
```

#### 7. Update Documentation

Update these files:

- **README.md**: Add tool descriptions, examples, update tool count
- **CHANGELOG.md**: Create new version section, document new tools
- **IMPLEMENTATION_PROGRESS.md**: Mark tasks as complete

## Common Patterns

### Error Handling

Always use try-except blocks with specific error types:

```python
try:
    result = await ha_client.api_method()
except ValueError as e:
    return [TextContent(type="text", text=f"Invalid input: {e}")]
except PermissionError as e:
    return [TextContent(type="text", text=f"Permission denied: {e}")]
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return [TextContent(type="text", text=f"Error: {e}")]
```

### Output Formatting

Use markdown formatting for tool outputs:

```python
result = "# Main Title\n\n"
result += "## Section\n\n"
result += f"- **Bold Label**: {value}\n"
result += f"- Status: {'✅' if success else '❌'}\n\n"
result += "## 💡 Next Steps\n\n"
result += "- Suggestion 1\n"
result += "- Suggestion 2\n"
```

### API Request Pattern

```python
# Supervisor API (addons, backups, system)
result = await self._make_request(
    "POST",
    f"{self.hassio_url}/endpoint",
    use_ha_token=False,
    json=payload
)

# Core API (entities, integrations, services)
result = await self._make_request(
    "GET",
    f"{self.ha_url}/api/endpoint",
    use_ha_token=True
)
```

## Configuration System

### Tool Toggle System

Each tool can be individually enabled/disabled:

1. **Environment Variable**: `TOOL_TOOL_NAME` (uppercase, underscores)
2. **Config Option**: `tool_tool_name` (lowercase, underscores)
3. **Default**: `true` (all tools enabled by default)

The system reads environment variables set by Home Assistant from the addon configuration.

### Token Requirements

- **SUPERVISOR_TOKEN**: Automatically provided by Home Assistant (always available)
- **ha_token**: Must be configured by user (required for entity/integration tools)

## Testing Approach

When testing new tools:

1. **Syntax Check**: Ensure no Python syntax errors
2. **Import Check**: Verify all imports are correct
3. **API Test**: Test API methods with real Home Assistant instance
4. **Tool Test**: Call tools through MCP interface
5. **Error Test**: Test error handling with invalid inputs
6. **Documentation**: Verify examples in README work

## File Structure

```
ha_full_mcp/
├── src/
│   ├── __init__.py
│   ├── server.py           # Main entry point
│   ├── config.py           # Configuration management
│   ├── ha_client.py        # API client (imports from api/)
│   ├── mcp_handlers.py     # MCP protocol handlers
│   ├── routes.py           # HTTP/SSE transport
│   ├── auth.py             # Authentication
│   ├── api/                # API client modules (refactored)
│   │   ├── __init__.py         # 26 lines - exports HomeAssistantClient
│   │   ├── base_client.py      # 75 lines - auth & requests
│   │   ├── addon_api.py        # 484 lines - addon management
│   │   ├── system_api.py       # 188 lines - logs, config, restart
│   │   ├── backup_api.py       # 81 lines - backup operations
│   │   ├── integration_api.py  # 89 lines - integration management
│   │   └── entity_api.py       # 101 lines - entity & service operations
│   └── tools/
│       ├── __init__.py
│       ├── addon/              # 22 addon tools (refactored into modules)
│       │   ├── __init__.py                 # 68 lines - router
│       │   ├── definitions.py              # 323 lines - tool schemas
│       │   ├── basic_handlers.py           # 64 lines - list, info
│       │   ├── lifecycle_handlers.py       # 156 lines - start, stop, restart, logs, update
│       │   ├── addon_config_handlers.py    # 351 lines - addon configuration
│       │   ├── management_handlers.py      # 432 lines - install, uninstall
│       │   ├── store_handlers.py           # 379 lines - store, rebuild, availability
│       │   ├── logs_handlers.py            # 266 lines - system logs, HA restart
│       │   └── config_file_handlers.py     # 342 lines - config file operations
│       ├── backup_tools.py     # 5 backup tools (371 lines)
│       ├── integration_tools.py # 4 integration tools (257 lines)
│       └── entity_tools.py     # 6 entity tools (425 lines)
├── config.yaml             # Addon configuration schema
├── Dockerfile              # Container build
├── requirements.txt        # Python dependencies
├── README.md              # User documentation
├── CHANGELOG.md           # Version history
└── .kiro/
    └── steering/
        ├── ha-mcp-development.md    # This file
        └── file-size-guidelines.md  # File size best practices
```

## Version History

- **1.6.0**: Added dashboard and automation management (12 new tools) ✅ COMPLETE
  - Dashboard tools: list, get config, create, delete dashboards
  - Automation tools: full CRUD operations, enable/disable, trigger
  - WebSocket client implementation for advanced features
  - All 49 tools tested and working correctly
- **1.5.0**: WebSocket implementation and automation foundation
- **1.4.2**: Major code refactoring for maintainability ✅ COMPLETE
  - Refactored addon_tools.py (2,005 lines) into 9 focused modules in `src/tools/addon/`
  - All Python files now under 500 lines for better AI compatibility
  - Created modular structure: definitions, basic_handlers, lifecycle_handlers, addon_config_handlers, management_handlers, store_handlers, logs_handlers, config_file_handlers
  - No functional changes - all 37 tools tested and working correctly
  - Improved code organization with clear separation of concerns
- **1.4.1**: Fixed integration tools API access (changed to http://homeassistant:8123)
  - All integration tools now working correctly
  - Fixed 401 Unauthorized errors
  - Tested all backup and integration tools successfully
- **1.4.0**: Added backup, integration, entity management (15 new tools)
  - Note: Integration tools use domain-based management via REST API
  - Full integration config entry management requires WebSocket API (future enhancement)
- **1.3.5**: Added config validation tool
- **1.3.3**: Added HA logs, config file read/write (4 new tools)
- **1.3.0**: Added individual tool toggles
- **1.2.0**: Renamed to "HA Full MCP Server"
- **1.1.0**: Added restart_homeassistant
- **1.0.0**: Production release with 17 tools
- **0.6.0**: Initial release with 7 core tools

## Common Issues & Solutions

### Import Errors
- Ensure all tool modules are imported in `mcp_handlers.py`
- Check that `__init__.py` exists in `src/tools/`

### API Authentication Errors
- Supervisor API: Uses `SUPERVISOR_TOKEN` (automatic)
- Core API: Requires `ha_token` in config (user must set)

### Tool Not Appearing
- Check tool is in `get_*_tool_definitions()` return list
- Verify tool name is in `all_tools` dict in `config.py`
- Ensure tool toggle is in `config.yaml` options and schema
- Check tool is not filtered by `enabled_tools` list

### API Endpoint Errors
- Supervisor API: `http://supervisor/...`
- Core API: `http://supervisor/core/api/...`
- Never use `localhost` or external URLs

## Best Practices

1. **Always validate inputs** before making API calls
2. **Use descriptive error messages** that help users understand what went wrong
3. **Log important operations** for debugging
4. **Format outputs consistently** using markdown
5. **Provide next steps** in tool outputs
6. **Test with real Home Assistant** before committing
7. **Update all documentation** when adding features
8. **Follow existing patterns** for consistency
9. **Default tools to enabled** (true) in config
10. **Use appropriate API** (Supervisor vs Core) for each operation
11. **Keep files under 500 lines** - see file-size-guidelines.md for details
12. **Split large files** by domain, responsibility, or feature
13. **Use mixins** for organizing API methods by domain

## Quick Reference

### Adding a Simple Tool (Checklist)

- [ ] Add tool definition to appropriate `tools/*.py` file
- [ ] Add tool handler in same file
- [ ] Add API method to `ha_client.py`
- [ ] Import tool module in `mcp_handlers.py`
- [ ] Add to tool list in `create_list_tools_handler`
- [ ] Add to routing in `create_call_tool_handler`
- [ ] Add to `all_tools` dict in `config.py`
- [ ] Add toggle to `config.yaml` options
- [ ] Add toggle to `config.yaml` schema
- [ ] Update README.md with description and examples
- [ ] Update CHANGELOG.md with new version entry
- [ ] Test tool with real Home Assistant instance

---

**Last Updated**: 2026-02-15  
**Maintainer**: Use this guide when context resets to quickly understand the codebase structure and patterns.
