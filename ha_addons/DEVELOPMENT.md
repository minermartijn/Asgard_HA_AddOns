# Development Guide - Home Assistant MCP Server

## Project Overview

The Home Assistant MCP Server is a production-ready Model Context Protocol implementation providing 18 management tools.

✅ **Status**: Version 1.1.0 (Stable)

## Architecture

The project follows a modular structure:
- **`src/server.py`**: Main entry point, sets up Starlette/uvicorn and SSE transport.
- **`src/ha_client.py`**: Aiohttp client for Home Assistant Core and Supervisor APIs.
- **`src/mcp_handlers.py`**: MCP protocol logic (tool routing, resource definitions).
- **`src/tools/addon_tools.py`**: Implementation of all 18 management tools.
- **`src/auth.py`**: Constant-time API key verification logic.

## Environment Setup

### 1. Prerequisites
- Python 3.11+
- `pip install -r requirements.txt`

### 2. Local Testing
To run the server locally for development:
```bash
export HA_TOKEN="your_token"
export API_KEY="your_key"
export TRANSPORT="sse"
export PORT="8015"
python3 src/server.py
```

### 3. MCP Inspector
Use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to verify tool definitions:
```bash
npx @modelcontextprotocol/inspector http://localhost:8015/sse?api_key=your_key
```

## Adding New Tools

### 1. Define the Tool
Add the tool definition in `src/tools/addon_tools.py` within the `get_addon_tool_definitions()` function. Follow the JSON Schema format for `inputSchema`.

### 2. Implement the Client Logic
If the tool requires a new API endpoint, add the corresponding method to `HomeAssistantClient` in `src/ha_client.py`.

### 3. Implement the Handler
Add the execution logic in the `handle_addon_tool()` function in `src/tools/addon_tools.py`.

### 4. Route the Tool
Ensure the tool name is added to the `addon_tools` list in `src/mcp_handlers.py` to ensure proper routing.

## Security Standards

- **Authentication**: All new endpoints must use the verification functions in `auth.py`.
- **Timing Attacks**: Use `secrets.compare_digest` for all sensitive comparisons.
- **Logging**: Never log full tokens or API keys (except during initial auto-generation).
- **Errors**: Provide helpful Markdown-formatted error messages but avoid leaking system internals.

## Testing Checklist
- [ ] Tool appears in `list_tools`.
- [ ] Input validation works (rejects missing/wrong type arguments).
- [ ] Error cases (404, 403, 500) are handled gracefully.
- [ ] Output is well-formatted Markdown.
- [ ] Async operations (like installs) are tracked correctly.

## Release Process
1. Update `version` in `config.yaml`.
2. Update `server_version` in `src/config.py`.
3. Update `CHANGELOG.md` with new features and fixes.
4. Update `QUICKSTART.md` if tool counts or instructions change.
5. Update `IMPLEMENTATION_SUMMARY.md`.
