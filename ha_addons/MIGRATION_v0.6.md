# Migration Guide: v0.5.x to v0.6.0

## What Changed

Version 0.6.0 introduces **standard MCP SSE transport** support, replacing the custom JSON-RPC implementation. This makes the addon compatible with all standard MCP clients.

## Breaking Changes

### 1. Endpoint URL Changed
- **Old**: `http://your-ha-ip:8015/mcp`
- **New**: `http://your-ha-ip:8015/sse`

### 2. Transport Configuration
- **Old**: `transport: streamable-http`
- **New**: `transport: sse`

### 3. Protocol Implementation
- **Old**: Custom JSON-RPC over HTTP
- **New**: Standard MCP SSE (Server-Sent Events)

## Migration Steps

### Step 1: Update Addon Configuration

In Home Assistant, update your addon configuration:

```yaml
# Change this:
transport: streamable-http

# To this:
transport: sse
```

### Step 2: Update MCP Client Configuration

If you were using a custom MCP client configuration, update the endpoint:

**Kiro Configuration** (`.kiro/settings/mcp.json`):
```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://YOUR_HA_IP:8015/sse",  // Changed from /mcp to /sse
      "transport": "sse",
      "disabled": false
    }
  }
}
```

### Step 3: Restart the Addon

1. Save the configuration changes
2. Restart the Home Assistant MCP Server addon
3. Check the logs to verify SSE transport is active:
   ```
   Using SSE (Server-Sent Events) transport
   MCP SSE endpoint: http://0.0.0.0:8015/sse
   ```

### Step 4: Reconnect Your MCP Client

1. Restart your MCP client (Kiro, Claude Desktop, etc.)
2. Or use the MCP Server view to manually reconnect
3. Verify the connection is working

## Benefits of v0.6.0

### Standard Compatibility
- Works with all standard MCP clients out of the box
- No custom protocol implementation needed
- Better interoperability

### Improved Reliability
- Uses official MCP SDK transport
- Better error handling
- More stable connections

### Future-Proof
- Follows MCP specification
- Will receive updates with MCP SDK
- Better long-term support

## Troubleshooting

### "Connection Refused" Error

**Cause**: Still using old endpoint URL

**Solution**: Update to `/sse` endpoint in your client configuration

### "Transport Not Supported" Error

**Cause**: Old transport setting in addon config

**Solution**: Change `transport: streamable-http` to `transport: sse`

### Tools Not Appearing

**Cause**: Client not properly connected to new endpoint

**Solution**: 
1. Verify endpoint URL ends with `/sse`
2. Restart both addon and client
3. Check addon logs for connection attempts

### Still Using Old Version

**Cause**: Addon not updated

**Solution**:
1. Check addon version in Home Assistant
2. Should show "0.6.0" or higher
3. Update if necessary and restart

## Rollback (If Needed)

If you need to rollback to v0.5.x:

1. Reinstall v0.5.x of the addon
2. Restore old configuration:
   ```yaml
   transport: streamable-http
   ```
3. Update client to use `/mcp` endpoint
4. Restart addon

**Note**: v0.5.x is not compatible with standard MCP clients. Rollback only if you have a custom client implementation.

## Support

For issues during migration:
1. Check addon logs in Home Assistant
2. Verify configuration matches this guide
3. Test connection with `curl http://YOUR_HA_IP:8015/sse`
4. Report issues with full logs and configuration

## What's Next

Future versions will add:
- Entity management tools
- Automation control
- Device management
- System control features

All future updates will maintain SSE transport compatibility.
