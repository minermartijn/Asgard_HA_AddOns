# ✓ Home Assistant MCP Server - Ready to Use!

## Status: WORKING ✓

Your Home Assistant MCP Server addon is now fully functional and ready to connect with Kiro!

## Server Information

- **Endpoint**: `http://192.168.1.84:8015/sse`
- **Transport**: SSE (Server-Sent Events)
- **Status**: Running and accepting connections
- **Available Tools**: 7 addon management tools

## Connect from Kiro

### Step 1: Create MCP Configuration

Create or edit the file `.kiro/settings/mcp.json` in your workspace:

```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://192.168.1.84:8015/sse",
      "transport": "sse",
      "disabled": false,
      "autoApprove": ["list_addons", "get_addon_info"]
    }
  }
}
```

### Step 2: Restart Kiro

After saving the configuration, restart Kiro or reload the MCP servers.

### Step 3: Verify Connection

1. Open the MCP Server view in Kiro
2. Look for "home-assistant" in the list
3. Check that it shows as connected

### Step 4: Test It!

Try these commands in Kiro:

```
"List all my Home Assistant addons"
"Show me information about the Mosquitto addon"
"Get the logs for the Node-RED addon"
"What addons do I have installed?"
```

## Available Tools

Your server provides these 7 tools:

1. **list_addons** - List all installed Home Assistant addons
2. **get_addon_info** - Get detailed information about a specific addon
3. **start_addon** - Start a stopped addon
4. **stop_addon** - Stop a running addon
5. **restart_addon** - Restart an addon
6. **get_addon_logs** - View logs from an addon
7. **update_addon** - Update an addon to the latest version

## Example Usage

Once connected, you can interact with your Home Assistant addons through natural language:

**List addons:**
```
You: "What addons do I have?"
Kiro: [Shows list of all installed addons with status]
```

**Get addon info:**
```
You: "Tell me about the Mosquitto broker addon"
Kiro: [Shows detailed information including version, state, resources]
```

**View logs:**
```
You: "Show me the logs for Studio Code Server"
Kiro: [Displays recent logs from the addon]
```

**Update addon:**
```
You: "Update the Node-RED addon"
Kiro: [Checks for updates, updates if available, shows progress]
```

## Troubleshooting

### Kiro Can't Connect

1. Verify the addon is running in Home Assistant
2. Check the URL is correct: `http://192.168.1.84:8015/sse`
3. Ensure port 8015 is accessible from your machine
4. Check for JSON syntax errors in `mcp.json`
5. Restart Kiro after configuration changes

### Tools Not Working

1. Check if you've set the `ha_token` in addon configuration
2. Verify the token is valid
3. Check addon logs for errors

### Connection Test

Run this command to verify the endpoint is accessible:

```bash
curl -v http://192.168.1.84:8015/sse
```

You should see:
- Status: `200 OK`
- Content-Type: `text/event-stream; charset=utf-8`

## What's Next

### Current Features (v0.6.0)
- ✓ Full addon management
- ✓ Addon logs access
- ✓ Addon updates with progress tracking
- ✓ Standard MCP SSE transport

### Coming Soon
- Entity state management
- Service calls
- Device management
- Automation control
- System control features

## Configuration Reference

### Addon Configuration (Home Assistant)

```yaml
log_level: info
host: "0.0.0.0"
port: 8015
transport: sse
ha_token: "your-long-lived-access-token"  # Optional but recommended
```

### Kiro Configuration

**Workspace-level** (`.kiro/settings/mcp.json`):
```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://192.168.1.84:8015/sse",
      "transport": "sse",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**User-level** (`~/.kiro/settings/mcp.json`):
Same format as above, but applies globally across all workspaces.

## Support

- **Setup Guide**: See [KIRO_SETUP.md](KIRO_SETUP.md)
- **Quick Reference**: See [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Full Documentation**: See [README.md](README.md)

## Success Indicators

✓ Server is running on port 8015
✓ SSE endpoint responds with 200 OK
✓ Content-Type is text/event-stream
✓ 7 tools are available
✓ Both Supervisor and HA Core tokens are configured

**Your server is ready to use with Kiro!**

---

Last tested: 2026-02-13 23:17 UTC
Server: http://192.168.1.84:8015/sse
Status: ✓ WORKING
