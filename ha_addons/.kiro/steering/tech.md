# Technology Stack

## Core Technologies

- **Language**: Python 3.x
- **MCP Framework**: `mcp[cli]>=1.0.0` (Model Context Protocol)
- **HTTP Server**: Uvicorn (ASGI) with Starlette framework
- **Transport**: SSE (Server-Sent Events) via `sse-starlette>=2.0.0`
- **HTTP Client**: `aiohttp>=3.9.0` for Home Assistant API calls
- **WebSocket**: `websockets>=12.0` for real-time HA communication

## Key Libraries

- `pydantic>=2.0.0` - Data validation and settings management
- `python-dateutil>=2.8.0` - Date/time utilities
- `starlette>=0.37.0` - ASGI web framework
- `uvicorn>=0.30.0` - ASGI server

## Project Structure

```
src/
├── server.py          # Main MCP server entry point
├── config.py          # Configuration management
├── ha_client.py       # Home Assistant API client
├── mcp_handlers.py    # MCP protocol handlers
├── routes.py          # HTTP route handlers
└── tools/
    └── addon_tools.py # Add-on management tools
```

## Build & Deployment

### Container Build
- **Dockerfile**: Multi-architecture container (aarch64, amd64, armhf, armv7, i386)
- **Base**: Home Assistant add-on base image
- **Config**: `config.yaml` defines add-on manifest and permissions

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (development)
python src/server.py

# Or build as Home Assistant add-on
# Copy to /addons/ha_mcp_server/ and install via HA UI
```

## Common Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run server locally
export LOG_LEVEL=info
export HOST=0.0.0.0
export PORT=8015
python src/server.py

# Test with MCP Inspector
npx -y @modelcontextprotocol/inspector
```

### Testing
```bash
# Test SSE connection
python test_sse_connection.py

# Test MCP client
python test_mcp_client.py
```

### Add-on Management
```bash
# Generate new API key
python generate_api_key.py

# Start add-on (via Home Assistant)
# Access at: http://<ha-ip>:8015/sse
```

## Addon Information

When working with this addon via Home Assistant APIs:
- **Addon Slug**: `local_ha_mcp_server_addon_kiro`
- **Display Name**: Home Assistant KIRO MCP Server ADDON
- **Version**: 0.6.0

Use the slug `local_ha_mcp_server_addon_kiro` for all addon management operations (logs, restart, etc.).

## Configuration

### Environment Variables
- `LOG_LEVEL`: Logging level (debug, info, warning, error)
- `HOST`: Server bind address (default: 0.0.0.0)
- `PORT`: Server port (default: 8015)
- `TRANSPORT`: Transport type (sse or stdio)
- `SUPERVISOR_TOKEN`: Auto-provided by Home Assistant
- `HA_TOKEN`: Long-lived access token (optional, for Core API)
- `API_KEY`: Authentication key for MCP endpoint

### Add-on Configuration (config.yaml)
```yaml
log_level: info
host: "0.0.0.0"
port: 8015
transport: sse
ha_token: ""
api_key: ""
```

## API Endpoints

- `GET /sse` - SSE connection endpoint
- `POST /messages` - Message handling (legacy)
- `GET /sse/{api_key}` - SSE with path-based auth
- `POST /messages/{api_key}` - Messages with path-based auth (Cloudflare-compatible)

## Authentication

API key required via:
1. Path parameter: `/messages/{api_key}` (RECOMMENDED for Cloudflare)
2. Query parameter: `?api_key=xxx`
3. Authorization header: `Bearer {api_key}`
4. X-API-Key header: `{api_key}`
