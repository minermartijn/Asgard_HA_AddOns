# Home Assistant MCP Server - Design Document

## Architecture Overview

The Home Assistant MCP Server is built as a layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Client (Kiro/IDE)                    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/SSE
                         │ (via Cloudflare)
┌────────────────────────┴────────────────────────────────────┐
│              Home Assistant MCP Server Add-on                │
│                                                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Starlette ASGI Application                  │   │
│  │  - CORS Middleware                                  │   │
│  │  - Route Handlers (SSE, Messages)                   │   │
│  │  - Authentication (API Key)                         │   │
│  └──────┬──────────────────────────┬───────────────────┘   │
│         │                          │                         │
│  ┌──────┴──────────┐      ┌───────┴────────────┐          │
│  │  MCP Server     │      │  Route Handlers    │          │
│  │  - list_tools   │      │  - SSE Handler     │          │
│  │  - call_tool    │      │  - Messages Handler│          │
│  │  - resources    │      │  - Auth Middleware │          │
│  └──────┬──────────┘      └────────────────────┘          │
│         │                                                    │
│  ┌──────┴──────────┐                                       │
│  │  Tool Modules   │                                       │
│  │  - addon_tools  │                                       │
│  └──────┬──────────┘                                       │
│         │                                                    │
│  ┌──────┴──────────┐                                       │
│  │  HA Client      │                                       │
│  │  - Supervisor   │                                       │
│  │  - Core API     │                                       │
│  └──────┬──────────┘                                       │
└─────────┼─────────────────────────────────────────────────┘
          │
          │ HTTP REST API
          │
┌─────────┴─────────────────────────────────────────────────┐
│              Home Assistant Supervisor                      │
│  - Add-on Management                                        │
│  - System Control                                           │
└─────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Server Entry Point (`src/server.py`)

**Responsibilities:**
- Load configuration from environment/options
- Initialize Home Assistant client
- Create MCP server instance
- Register MCP handlers
- Create SSE transport with API key in path
- Set up Starlette application with routes
- Start Uvicorn server

**Key Design Decisions:**
- Use factory pattern for route handlers (dependency injection)
- Embed API key in SSE transport path for Cloudflare compatibility
- Support both SSE and stdio transports (stdio for future use)

### 2. Configuration Management (`src/config.py`)

**Responsibilities:**
- Load configuration from environment variables
- Load configuration from Home Assistant options
- Validate configuration
- Provide configuration object to other components

**Configuration Schema:**
```python
@dataclass
class Config:
    log_level: str
    host: str
    port: int
    transport_type: str  # "sse" or "stdio"
    ha_token: str | None
    api_key: str
    server_name: str
    server_version: str
```

### 3. Home Assistant Client (`src/ha_client.py`)

**Responsibilities:**
- Manage authentication tokens (Supervisor and Core)
- Make HTTP requests to Home Assistant APIs
- Handle API errors and retries
- Provide high-level methods for add-on operations

**API Methods:**
```python
class HomeAssistantClient:
    # Add-on Management
    async def list_addons() -> list[dict]
    async def get_addon_info(slug: str) -> dict
    async def start_addon(slug: str) -> dict
    async def stop_addon(slug: str) -> dict
    async def restart_addon(slug: str) -> dict
    async def update_addon(slug: str) -> dict
    async def get_addon_logs(slug: str) -> str
    async def check_addon_update(slug: str) -> dict
    async def refresh_updates() -> dict
```

**Authentication Strategy:**
- Use `SUPERVISOR_TOKEN` env var for Supervisor API
- Use long-lived token from config for Core API
- Switch tokens based on `use_ha_token` parameter

### 4. MCP Handlers (`src/mcp_handlers.py`)

**Responsibilities:**
- Implement MCP protocol handlers
- Route tool calls to appropriate tool modules
- Manage resources (future: entity lists, device lists)

**Handler Functions:**
```python
def create_list_tools_handler(ha_client) -> Callable
def create_call_tool_handler(ha_client) -> Callable
def create_list_resources_handler() -> Callable
def create_read_resource_handler() -> Callable
```

**Design Pattern:**
- Factory functions that close over dependencies (ha_client)
- Handlers are async functions
- Handlers return MCP protocol types

### 5. Route Handlers (`src/routes.py`)

**Responsibilities:**
- Handle HTTP requests for SSE and messages endpoints
- Authenticate requests using API key
- Delegate to SSE transport for message handling
- Return proper Response objects to Starlette

**Key Classes:**
```python
class AlreadySentResponse(Response):
    """Special response for handlers that send via ASGI directly"""
    async def __call__(self, scope, receive, send):
        pass  # Response already sent
```

**Route Handler Factories:**
```python
def create_sse_handler(sse, server, api_key, ...) -> Callable
def create_sse_handler_with_path_key(sse, server, api_key, ...) -> Callable
def create_messages_handler(sse, api_key) -> Callable
def create_messages_handler_with_path_key(sse, api_key) -> Callable
```

**Authentication Flow:**
1. Extract API key from path params, query params, or headers
2. Compare with configured API key
3. Return 401 if mismatch
4. Proceed with request if match

### 6. Tool Modules (`src/tools/`)

**Responsibilities:**
- Define MCP tool schemas
- Implement tool execution logic
- Format tool responses
- Handle tool-specific errors

**Tool Module Pattern:**
```python
# src/tools/addon_tools.py

def get_addon_tool_definitions() -> list[Tool]:
    """Return list of Tool objects with schemas"""
    return [
        Tool(
            name="list_addons",
            description="...",
            inputSchema={...}
        ),
        # ... more tools
    ]

async def handle_addon_tool(
    name: str,
    arguments: dict,
    ha_client: HomeAssistantClient
) -> list[TextContent]:
    """Execute addon tool and return formatted response"""
    if name == "list_addons":
        addons = await ha_client.list_addons()
        result = format_addons(addons)
        return [TextContent(type="text", text=result)]
    # ... more tool handlers
```

### 7. Authentication (`src/auth.py`)

**Responsibilities:**
- Verify API key from various sources
- Support path-based, query-based, and header-based auth
- Log authentication attempts

**Authentication Functions:**
```python
def verify_api_key(request: Request, api_key: str) -> bool:
    """Check query params and headers"""
    
def verify_path_api_key(request: Request, api_key: str) -> bool:
    """Check path parameters"""
```

## Data Flow

### Tool Execution Flow

1. **Client Request**: MCP client sends tool call via POST to `/messages/{api_key}`
2. **Authentication**: Route handler verifies API key from path
3. **SSE Transport**: `sse.handle_post_message()` receives request
4. **MCP Server**: Parses MCP protocol message (CallToolRequest)
5. **Tool Handler**: `call_tool_handler` routes to appropriate tool module
6. **Tool Execution**: Tool module calls HA client methods
7. **HA API**: Client makes HTTP request to Supervisor API
8. **Response Formatting**: Tool module formats response as TextContent
9. **MCP Response**: Server sends CallToolResult back through SSE
10. **Client Receives**: MCP client receives formatted response

### SSE Connection Flow

1. **Client Connects**: GET request to `/sse` or `/sse/{api_key}`
2. **Authentication**: Verify API key
3. **SSE Context**: `sse.connect_sse()` creates read/write streams
4. **MCP Initialization**: Send InitializationOptions to client
5. **Server Run**: `server.run()` processes messages from client
6. **Keep-Alive**: SSE connection stays open for bidirectional communication

## Security Design

### API Key Management

**Generation:**
```python
import secrets
api_key = secrets.token_urlsafe(32)  # 256 bits of entropy
```

**Storage:**
- Stored in add-on configuration (config.yaml options)
- Logged on startup (user must save it)
- Never exposed in API responses

**Validation:**
- Constant-time comparison to prevent timing attacks
- Checked on every request
- Multiple auth methods supported (path, query, header)

### Cloudflare Compatibility

**Problem:** Cloudflare strips authentication headers

**Solution:** Embed API key in URL path
```python
# Server tells client to use this endpoint:
sse = SseServerTransport(f"/messages/{api_key}")

# Client sends messages to:
POST /messages/{api_key}?session_id=xxx

# Server extracts from path:
path_key = request.path_params.get("api_key")
```

**Why This Works:**
- URL paths are never stripped by proxies
- API key survives Cloudflare transformation
- Still secure over HTTPS

### Token Isolation

**Supervisor Token:**
- Auto-provided by Home Assistant
- Used for add-on management only
- Never exposed to client

**Core Token:**
- User-provided long-lived token
- Used for entity/service operations
- Optional (not needed for add-on tools)

## Error Handling Design

### Error Categories

1. **Authentication Errors**: 401 Unauthorized
2. **Not Found Errors**: 404 with descriptive message
3. **API Errors**: Caught and logged, returned as tool error
4. **Network Errors**: Retry logic, timeout handling
5. **Validation Errors**: 400 Bad Request

### Error Response Format

```python
# Tool execution error
return [TextContent(
    type="text",
    text=f"Error: {error_message}"
)]

# HTTP error
return JSONResponse(
    {"error": "Descriptive message"},
    status_code=401,
    headers={"WWW-Authenticate": "Bearer"}
)
```

### Logging Strategy

```python
# Configuration logging
logger.info("Configuration loaded: ...")

# Authentication logging
logger.warning("Unauthorized attempt from {ip}")

# Tool execution logging
logger.info("Tool called: {name} with arguments: {args}")

# Error logging
logger.error("API request failed: {error}")
```

## Performance Considerations

### Async/Await

All I/O operations use async/await:
```python
async def list_addons(self) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

### Connection Pooling

- aiohttp manages connection pooling automatically
- Sessions are created per request (lightweight)
- No persistent connections needed (stateless)

### Response Streaming

- SSE transport streams responses
- Large logs are truncated (10,000 chars max)
- No buffering of entire responses

## Extensibility Design

### Adding New Tools

1. Create tool module in `src/tools/`
2. Implement `get_*_tool_definitions()`
3. Implement `handle_*_tool()`
4. Import in `src/mcp_handlers.py`
5. Add to tool list and call handler

Example:
```python
# src/tools/entity_tools.py
def get_entity_tool_definitions() -> list[Tool]:
    return [Tool(name="list_entities", ...)]

async def handle_entity_tool(name, args, ha_client):
    if name == "list_entities":
        entities = await ha_client.get_states()
        return [TextContent(type="text", text=format_entities(entities))]
```

### Adding New Resources

1. Add resource definition in `create_list_resources_handler()`
2. Add handler logic in `create_read_resource_handler()`

Example:
```python
resources = [
    Resource(
        uri="ha://entities/list",
        name="Entity List",
        description="List of all entities"
    )
]
```

## Testing Strategy

### Unit Tests (Future)

- Test each tool handler with mock HA client
- Test authentication functions
- Test configuration loading
- Test error handling

### Integration Tests (Current)

- Manual testing with MCP Inspector
- Manual testing with Kiro
- Test all tools end-to-end
- Test authentication scenarios
- Test error cases

### Test Checklist

- [ ] SSE connection establishes
- [ ] API key authentication works
- [ ] All 7 tools execute successfully
- [ ] Errors return proper status codes
- [ ] Logs are clean (no TypeErrors)
- [ ] Works through Cloudflare proxy
- [ ] Handles invalid inputs gracefully

## Deployment Design

### Add-on Packaging

**Manifest (config.yaml):**
```yaml
name: Home Assistant KIRO MCP Server ADDON
version: "0.6.0"
slug: ha_mcp_server_addon_kiro
arch: [aarch64, amd64, armhf, armv7, i386]
ports:
  8015/tcp: 8015
homeassistant_api: true
hassio_api: true
supervisor_api: true
```

**Dockerfile:**
- Multi-stage build
- Python 3.11 base
- Install dependencies from requirements.txt
- Copy source code
- Set entrypoint to run.sh

**Startup Script (run.sh):**
```bash
#!/usr/bin/with-contenv bashio
bashio::log.info "Starting Home Assistant MCP Server..."
python3 /app/src/server.py
```

### Configuration Options

Users can configure via Home Assistant UI:
- log_level: debug|info|warning|error
- host: IP address to bind
- port: Port number
- transport: sse|stdio
- ha_token: Long-lived access token
- api_key: Custom API key

## Future Enhancements

### Phase 2: Entity Management
- list_entities tool
- get_entity_state tool
- call_service tool
- Entity filtering by domain

### Phase 3: Device Management
- list_devices tool
- get_device_info tool
- detect_ghost_entities tool
- remove_entity tool (with confirmation)

### Phase 4: System Control
- restart_core tool
- restart_host tool
- backup_create tool
- backup_restore tool

### Phase 5: Advanced Features
- WebSocket-based real-time updates
- Entity state subscriptions
- Automation management
- Scene management

## Correctness Properties

### Property 1: Authentication Consistency
**Validates: Requirements US-2 (Secure Remote Access)**

For all requests to protected endpoints:
- If API key matches configured key → 200/202 response
- If API key doesn't match → 401 response
- No requests succeed without valid API key

### Property 2: Tool Execution Idempotency
**Validates: Requirements US-1 (Remote Add-on Management)**

For read-only tools (list_addons, get_addon_info, get_addon_logs):
- Multiple calls with same arguments return same result
- No side effects on Home Assistant state
- Results are deterministic

### Property 3: API Key Path Preservation
**Validates: Requirements TR-3 (Cloudflare Compatibility)**

For all message requests:
- API key in path is extracted correctly
- API key survives proxy transformation
- Authentication succeeds through Cloudflare

### Property 4: Error Response Completeness
**Validates: Requirements US-7 (Clean Error Handling)**

For all error conditions:
- Error response includes descriptive message
- Error response includes appropriate status code
- Error is logged with sufficient detail
- Server continues operating after error

### Property 5: Tool Response Format Consistency
**Validates: Requirements TR-1 (MCP Protocol Compliance)**

For all tool executions:
- Response is list of TextContent objects
- Response includes formatted output
- Response follows MCP protocol types
- Response is parseable by MCP clients

## Design Decisions Log

### Decision 1: Embed API Key in Path
**Context:** Cloudflare strips authentication headers
**Decision:** Use `/messages/{api_key}` endpoint
**Rationale:** URL paths survive all proxies
**Alternatives Considered:** Query params (not preserved), headers (stripped), session-based (complex)

### Decision 2: Use AlreadySentResponse Class
**Context:** sse.handle_post_message() returns None, causing TypeError
**Decision:** Return custom Response subclass that does nothing
**Rationale:** Satisfies Starlette routing without double-sending
**Alternatives Considered:** Raw ASGI (complex), exception handler (hacky), accept error (poor UX)

### Decision 3: Factory Pattern for Handlers
**Context:** Need to inject dependencies into handlers
**Decision:** Use factory functions that close over dependencies
**Rationale:** Clean dependency injection, testable, Pythonic
**Alternatives Considered:** Global state (bad), class-based (overkill), manual passing (verbose)

### Decision 4: Modular Tool Structure
**Context:** Need to support many tools across domains
**Decision:** Separate tool modules by domain (addon_tools, entity_tools, etc.)
**Rationale:** Maintainable, extensible, clear separation of concerns
**Alternatives Considered:** Single file (unmaintainable), per-tool files (too granular)

### Decision 5: Async/Await Throughout
**Context:** Need to handle concurrent requests efficiently
**Decision:** Use async/await for all I/O operations
**Rationale:** Non-blocking, efficient, standard Python pattern
**Alternatives Considered:** Threading (complex), sync (blocking), callbacks (callback hell)
