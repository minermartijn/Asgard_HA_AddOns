# HA Addon MCP Server (Lifeboat)

[![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)](https://github.com/minermartijn/Asgard_HA_AddOns)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-green.svg)](https://www.home-assistant.io/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-orange.svg)](https://modelcontextprotocol.io/)

A lightweight Model Context Protocol (MCP) server dedicated exclusively to Home Assistant app lifecycle management, logs, and emergency recovery.

## Why a Dedicated App Manager (The "Lifeboat" Pattern)?

If you use a comprehensive MCP server like **HA Full MCP Server** (port 8010) to manage your smart home, updating or troubleshooting that app itself creates a catch-22:
- If the AI assistant triggers an update of `ha_full_mcp` and the container goes down, rebuilds, or fails to start, the AI loses its entire connection to Home Assistant.
- The AI cannot inspect why the update broke or restart the container.

**HA Addon MCP Server** solves this by running independently on **port 8015**. It focuses purely on app operations:
- Checking app logs and supervisor logs
- Starting, stopping, restarting, and rebuilding apps
- Updating app configurations
- Rebuilding or restarting `ha_full_mcp` if an update fails

Because it relies solely on Home Assistant's internal Supervisor API (`SUPERVISOR_TOKEN`), it continues functioning even if other components or Core tokens are unavailable.

## What can it do? (22 Tools)

- **Monitor & Inspect**: `list_addons`, `get_addon_info`, `get_addon_logs`, `get_supervisor_logs`
- **Control**: `start_addon`, `stop_addon`, `restart_addon`
- **Maintain & Repair**: `update_addon`, `rebuild_addon`, `install_addon`, `uninstall_addon`
- **Configure**: `get_addon_configuration`, `set_addon_configuration`, `validate_addon_configuration`
- **Catalog**: `list_store_addons`, `reload_addons`, `check_addon_availability`
- **System**: `restart_homeassistant`
- **Backup & Restore**: `create_addon_backup`, `list_backups`, `get_backup_info`, `restore_addon_backup`

## Connecting AI Assistants

The app supports both modern **Streamable HTTP** (`/mcp`) and legacy **SSE** (`/sse`) transports concurrently on port **8015**.

### Streamable HTTP (Recommended)

Modern MCP clients (Cursor, Claude Desktop, Kiro) connect to:

- **Endpoint**: `http://YOUR-HA-IP:8015/mcp`
- **Path-based key (for Cloudflare Tunnels/proxies)**: `http://YOUR-HA-IP:8015/mcp/YOUR-API-KEY`
- **Health Check**: `http://YOUR-HA-IP:8015/health`

#### Configuration (`mcp.json`)

```json
{
  "mcpServers": {
    "ha-addons-lifeboat": {
      "url": "http://YOUR-HA-IP:8015/mcp",
      "headers": {
        "Authorization": "Bearer YOUR-API-KEY"
      }
    }
  }
}
```

Or behind Cloudflare Tunnel (where custom headers cannot be set):

```json
{
  "mcpServers": {
    "ha-addons-lifeboat": {
      "url": "https://lifeboat.yourdomain.com/mcp/YOUR-API-KEY"
    }
  }
}
```

### SSE (Server-Sent Events)

For clients using SSE:

- **URL**: `http://YOUR-HA-IP:8015/sse?api_key=YOUR-API-KEY`
- **Path-based SSE**: `http://YOUR-HA-IP:8015/sse/YOUR-API-KEY`

```json
{
  "mcpServers": {
    "ha-addons-lifeboat": {
      "url": "http://YOUR-HA-IP:8015/sse?api_key=YOUR-API-KEY",
      "transport": "sse"
    }
  }
}
```

## Recommended Dual-Server Setup

For maximum AI reliability, configure both servers in your AI assistant:

```json
{
  "mcpServers": {
    "home-assistant-full": {
      "url": "http://YOUR-HA-IP:8010/mcp",
      "headers": { "Authorization": "Bearer FULL-SERVER-API-KEY" }
    },
    "home-assistant-lifeboat": {
      "url": "http://YOUR-HA-IP:8015/mcp",
      "headers": { "Authorization": "Bearer LIFEBOAT-API-KEY" }
    }
  }
}
```

Now, your AI can freely manage entities and automations via the full server, while safely falling back to the lifeboat server to update, restart, or repair apps!

## Configuration Options

```yaml
log_level: info        # How chatty the logs are (debug, info, warning, error)
host: "0.0.0.0"       # Leave this alone unless you know what you're doing
port: 8015            # The port to run on
transport: sse        # Keep this as 'sse' for HTTP connections
ha_token: ""          # Optional: Long-lived access token for extra features
api_key: ""           # Your secret key - set this or one will be generated
```

The important one is `api_key`. Set it to something secure, or leave it blank and the app will generate a random one on first start. Either way, you'll need this key to connect your AI assistant.

## Example conversations

Once you've got this set up, you can do things like:

**You:** "What apps do I have installed?"  
**AI:** *Lists all your apps with their current status*

**You:** "Install the ESPHome app"  
**AI:** *Installs it and confirms when it's ready*

**You:** "The Node-RED app isn't working, can you check the logs?"  
**AI:** *Pulls the logs and helps you figure out what's wrong*

**You:** "Update all my apps"  
**AI:** *Checks for updates and installs them*

It's honestly pretty convenient once you get used to it.

## Security stuff

The app uses an API key to make sure only you (or your AI assistant) can control things. Keep that key private - anyone with it can manage your apps.

If you connect through Cloudflare or another reverse proxy, use HTTPS and an additional access restriction or authentication layer. Prefer sending the API key in a request header where supported. Path-based and query-string keys are supported for compatibility, but they can appear in proxy logs, copied URLs, browser history, and monitoring data. Protect those records and rotate exposed keys. Avoid directly exposing port 8015 to the public internet. See the [repository security policy](../SECURITY.md).

## Troubleshooting

**"Connection refused" or can't connect:**
- Make sure the app is actually running (check the app page)
- Verify you're using the right IP address and port
- Check that port 8015 isn't blocked by a firewall

**"Unauthorized" errors:**
- Double-check your API key matches what's in the app logs
- Make sure you copied the whole key without extra spaces

**App won't start:**
- Check the app logs for errors
- Make sure you don't have another service using port 8015

**Something else broken:**
- Check the app logs first
- Look at the supervisor logs (you can use the app itself to do this once it's running)
- Open an issue on GitHub with the logs

## Version

Current version: **1.4.0**

This is production-ready and stable. All 22 tools have automated coverage for their critical paths.

## What can you actually do with this?

Here's everything the app can do (22 tools total):

**Managing your apps:**
- See what's installed
- Get details about any app
- Start, stop, or restart apps
- Check app logs when troubleshooting
- Update apps to the latest version

**Installing stuff:**
- Install apps from the store
- Uninstall apps you don't need
- Rebuild custom apps from source

**Configuring apps:**
- View current app settings
- Change app configuration
- Test config changes before applying them

**Finding new apps:**
- Browse the entire app store
- Search for specific apps
- Check if an app works on your system before installing

**Debugging:**
- Read supervisor logs (super helpful when builds fail)

**System control:**
- Restart Home Assistant Core

**Backup and restore:**
- Create a partial backup containing exactly one app
- List and inspect backup metadata
- Restore exactly one app only after verifying that the backup contains its exact slug

All of this through simple conversations with your AI assistant. No clicking around in the UI.

## Contributing

Found a bug? Want a new feature? Pull requests and issues are welcome.

## License

This project follows standard open source practices. Check the repository for specific license details.

---

Built for people who'd rather chat with their AI assistant than click through menus. Works great with Kiro, Claude Desktop, and any other MCP-compatible tool.

---
Built with ⚡ by Asgard.

### Support my caffeine addiction ☕
If these apps saved you some time (or a headache), feel free to fuel my next coding session! My code is powered by high-quality caffeine—one cup equals approximately three features and only one new bug. 😉

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/minermartijn)
