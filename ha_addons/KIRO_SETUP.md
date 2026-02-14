# Setting Up Home Assistant MCP Server with Kiro

This guide will help you configure the Home Assistant MCP Server to work with Kiro IDE.

## Step 1: Generate an API Key

Run the API key generator:

```bash
python3 generate_api_key.py
```

This will output a secure random API key. Save this key - you'll need it for both the add-on configuration and Kiro.

## Step 2: Configure the Add-on

1. Open your Home Assistant instance
2. Navigate to Settings → Add-ons → Home Assistant MCP Server
3. Go to the Configuration tab
4. Add your configuration:

```yaml
ha_token: "your_home_assistant_long_lived_token"
api_key: "your_generated_api_key_from_step_1"
port: 8015
host: "0.0.0.0"
transport: sse
```

5. Save the configuration
6. Start (or restart) the add-on

## Step 3: Configure Kiro

1. Open Kiro IDE
2. Open your MCP configuration file (usually at `~/.kiro/settings/mcp.json`)
3. Add the Home Assistant MCP server:

```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://<your-home-assistant-ip>:8015/sse",
      "headers": {
        "Authorization": "Bearer <your-api-key-from-step-1>"
      }
    }
  }
}
```

Replace:
- `<your-home-assistant-ip>` with your Home Assistant IP address (e.g., `192.168.1.100`)
- `<your-api-key-from-step-1>` with the API key you generated

## Step 4: Test the Connection

1. Restart Kiro or reload the MCP configuration
2. In Kiro, you should now see the Home Assistant MCP server connected
3. Try listing available tools to verify the connection works

## Security Notes

- The API key protects your MCP endpoint from unauthorized access
- Keep your API key secure - treat it like a password
- If you expose this endpoint to the internet, consider using:
  - A reverse proxy with HTTPS (like Nginx Proxy Manager)
  - Additional firewall rules
  - VPN access

## Troubleshooting

### Connection Refused
- Check that the add-on is running
- Verify the port (8015) is accessible
- Check firewall settings

### Unauthorized (401) Error
- Verify the API key matches in both configurations
- Check that the Authorization header is properly formatted
- Look at the add-on logs for authentication attempts

### No Tools Available
- Check the add-on logs for errors
- Verify the `ha_token` is configured correctly
- Ensure the add-on has proper permissions

## Example Usage in Kiro

Once configured, you can ask Kiro to:
- "List all Home Assistant add-ons"
- "Show me the logs for the XYZ add-on"
- "Restart the ABC add-on"
- "Get information about the DEF add-on"

The MCP server will handle these requests securely using your API key.
