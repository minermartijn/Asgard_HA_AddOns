---
inclusion: always
---

# Home Assistant MCP Server - Architecture & Troubleshooting Guide

## Overview

This is a Model Context Protocol (MCP) server that provides remote access to Home Assistant add-on management through a standardized API. It runs as a Home Assistant add-on and exposes 7 tools for managing other add-ons.

## Architecture

### Transport Layer
- **Protocol**: SSE (Server-Sent Events) over HTTP/HTTPS
- **Framework**: Starlette (ASGI) with Uvicorn
- **Port**: 8015 (configurable)
- **Endpoints**:
  - `GET /sse` - SSE connection endpoint
  - `POST /messages/{api_key}` - Message handling endpoint (API key in path)
  - `GET /sse/{api_key}` - Alternative SSE endpoint with API key in path
  - `POST /messages` - Legacy message endpoint (requires headers/query params)

### Authentication
- **API Key**: Required for all requests
- **Methods** (in order of precedence):
  1. Path parameter: `/messages/{api_key}` (RECOMMENDED for Cloudflare)
  2. Query parameter: `?api_key=xxx`
  3. Authorization header: `Bearer {api_key}`
  4. X-API-Key header: `{api_key}`

### Key Components
- `src/server.py` - Main MCP server with SSE transport
- `src/ha_client.py` - Home Assistant API client
- `src/tools/addon_tools.py` - Add-on management tools
- `config.yaml` - Add-on configuration schema

## Available Tools

1. **list_addons** - List all installed add-ons
2. **get_addon_info** - Get detailed info about a specific add-on
3. **start_addon** - Start a stopped add-on
4. **stop_addon** - Stop a running add-on
5. **restart_addon** - Restart an add-on
6. **get_addon_logs** - Retrieve add-on logs
7. **update_addon** - Update an add-on to latest version

## Critical Issue: Cloudflare Authentication Problem

### The Problem
When using Cloudflare as a reverse proxy (tunnels, proxies, etc.), authentication headers are stripped or not forwarded to the backend server. This causes all requests to fail with 401 Unauthorized.

### Why It Happens
1. MCP clients (like Kiro) connect to `/sse` endpoint successfully
2. The SSE transport tells the client to use `/messages` for sending messages
3. Kiro constructs the `/messages` URL but **does NOT preserve query parameters** from the original `/sse` URL
4. Cloudflare strips `Authorization` and `X-API-Key` headers by default
5. Result: `/messages` requests arrive with no authentication

### The Solution
**Embed the API key in the messages endpoint path itself:**

```python
# In src/server.py, line ~165
sse = SseServerTransport(f"/messages/{api_key}")
```

This tells the MCP client to use `/messages/{api_key}` instead of `/messages`, and the API key survives the Cloudflare proxy because it's part of the URL path, not a header or query parameter.

### Implementation Details

```python
# Create message endpoint with API key in path
async def handle_messages_with_key(request: Request):
    """Handle POST messages with API key in path"""
    path_key = request.path_params.get("api_key", "")
    if path_key != api_key:
        logger.warning(f"Unauthorized message attempt from {request.client.host}")
        return JSONResponse(
            {"error": "Unauthorized - Invalid or missing API key"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Handle the message - this function sends response directly
    await sse.handle_post_message(request.scope, request.receive, request._send)
```

### Routes Configuration

```python
app = Starlette(
    routes=[
        Route("/sse", handle_sse, methods=["GET"]),
        Route("/messages", handle_messages, methods=["POST"]),
        Route("/sse/{api_key}", handle_sse_with_key, methods=["GET"]),
        Route("/messages/{api_key}", handle_messages_with_key, methods=["POST"]),
    ]
)
```

## Client Configuration

### For Cloudflare (RECOMMENDED)
```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "https://your-domain.com/sse?api_key=YOUR_API_KEY",
      "transport": "sse",
      "disabled": false
    }
  }
}
```

The query parameter in the URL is optional but helps with initial connection. The critical part is that the server is configured to use `/messages/{api_key}` as the messages endpoint.

### For Direct Connection (No Proxy)
```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://192.168.1.84:8015/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      },
      "disabled": false
    }
  }
}
```

## Known Issues

### TypeError: 'NoneType' object is not callable
**Status**: Cosmetic issue, does not affect functionality

**Symptoms**: Error appears in logs after successful requests (202 Accepted)

**Cause**: `sse.handle_post_message()` sends the response directly through `request._send` and returns None, but Starlette's routing expects a response object.

**Impact**: None - requests complete successfully before the error occurs

**Fix**: Would require refactoring to use raw ASGI handlers instead of Starlette Routes, but not worth the effort since functionality is perfect.

## Testing Checklist

When making changes to this server, test all tools:

1. ✅ Connect through Cloudflare tunnel
2. ✅ list_addons - Verify all add-ons appear
3. ✅ get_addon_info - Check version and state
4. ✅ stop_addon - Verify state changes to "stopped"
5. ✅ start_addon - Verify state changes to "started"
6. ✅ restart_addon - Check logs for restart sequence
7. ✅ get_addon_logs - Verify logs are retrieved
8. ✅ update_addon - Verify version number increases

## Debugging Tips

### Check Authentication
Look for these log patterns:
- `"GET /sse?api_key=xxx HTTP/1.1" 200 OK` - SSE connection successful
- `"POST /messages/{api_key}?session_id=xxx HTTP/1.1" 202 Accepted` - Message successful
- `"POST /messages?session_id=xxx HTTP/1.1" 401 Unauthorized` - API key not in path (PROBLEM)

### Verify API Key Configuration
```bash
# Check add-on configuration
ha addons info local_ha_mcp_server_addon_kiro

# Check logs for API key
docker logs addon_local_ha_mcp_server_addon_kiro
```

### Test Direct Connection
Bypass Cloudflare to isolate proxy issues:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://192.168.1.84:8015/sse
```

## Security Considerations

1. **API Key Storage**: Store in add-on configuration, not in code
2. **HTTPS**: Always use HTTPS in production (Cloudflare provides this)
3. **Key Rotation**: Change API key if exposed
4. **Network Isolation**: Consider restricting access to specific IPs in Cloudflare

## Future Improvements

1. Fix the NoneType error by using raw ASGI handlers
2. Add more tools (entity management, automation control, etc.)
3. Implement session-based authentication to avoid API key in URL
4. Add rate limiting
5. Support OAuth2 flow for better security
