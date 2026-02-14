# Home Assistant MCP Server

Control your Home Assistant addons from AI assistants like Claude, Kiro, or any MCP-compatible tool.

## What is this?

Ever wanted to ask Claude "hey, restart my Node-RED addon" or tell Kiro "install the ESPHome addon for me"? That's exactly what this does.

This addon turns your Home Assistant into an MCP server, which means AI assistants can talk to it directly. No more switching between your chat and the Home Assistant UI to manage addons - just ask your AI assistant to do it.

## What can it do?

Pretty much everything you'd do with addons in the Home Assistant UI:

- Install and uninstall addons from the store
- Start, stop, and restart addons
- Update addons to the latest version
- Change addon settings
- Check logs when something breaks
- Browse the addon store
- Even restart Home Assistant itself

It's like having a really smart assistant who knows their way around your Home Assistant setup.

## Installation

1. Add this repository to your Home Assistant addon store
2. Find "HA Addon MCP Server" and click Install
3. Go to the Configuration tab and set your API key (or let it generate one)
4. Start the addon
5. Check the logs for your API key if you didn't set one

That's it. Now you just need to connect your AI assistant to it.

## Quick Setup for Kiro

Add this to your Kiro MCP settings (`.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://YOUR-HA-IP:8015/sse?api_key=YOUR-API-KEY",
      "transport": "sse"
    }
  }
}
```

Replace `YOUR-HA-IP` with your Home Assistant's IP address and `YOUR-API-KEY` with the key from the addon logs.

**Using Cloudflare?** No worries, the addon handles that automatically. Just use your public URL instead of the local IP.

## Configuration Options

```yaml
log_level: info        # How chatty the logs are (debug, info, warning, error)
host: "0.0.0.0"       # Leave this alone unless you know what you're doing
port: 8015            # The port to run on
transport: sse        # Keep this as 'sse' for HTTP connections
ha_token: ""          # Optional: Long-lived access token for extra features
api_key: ""           # Your secret key - set this or one will be generated
```

The important one is `api_key`. Set it to something secure, or leave it blank and the addon will generate a random one on first start. Either way, you'll need this key to connect your AI assistant.

## Example conversations

Once you've got this set up, you can do things like:

**You:** "What addons do I have installed?"  
**AI:** *Lists all your addons with their current status*

**You:** "Install the ESPHome addon"  
**AI:** *Installs it and confirms when it's ready*

**You:** "The Node-RED addon isn't working, can you check the logs?"  
**AI:** *Pulls the logs and helps you figure out what's wrong*

**You:** "Update all my addons"  
**AI:** *Checks for updates and installs them*

It's honestly pretty convenient once you get used to it.

## Security stuff

The addon uses an API key to make sure only you (or your AI assistant) can control things. Keep that key private - anyone with it can manage your addons.

If you're exposing this through Cloudflare or another proxy, the addon handles authentication properly so it'll work fine. The API key gets embedded in the URL path, which survives proxy forwarding.

## Troubleshooting

**"Connection refused" or can't connect:**
- Make sure the addon is actually running (check the addon page)
- Verify you're using the right IP address and port
- Check that port 8015 isn't blocked by a firewall

**"Unauthorized" errors:**
- Double-check your API key matches what's in the addon logs
- Make sure you copied the whole key without extra spaces

**Addon won't start:**
- Check the addon logs for errors
- Make sure you don't have another service using port 8015

**Something else broken:**
- Check the addon logs first
- Look at the supervisor logs (you can use the addon itself to do this once it's running)
- Open an issue on GitHub with the logs

## Version

Current version: **1.2.0**

This is production-ready and stable. All 18 tools have been tested and work reliably.

## What can you actually do with this?

Here's everything the addon can do (18 tools total):

**Managing your addons:**
- See what's installed
- Get details about any addon
- Start, stop, or restart addons
- Check addon logs when troubleshooting
- Update addons to the latest version

**Installing stuff:**
- Install addons from the store
- Uninstall addons you don't need
- Rebuild custom addons from source

**Configuring addons:**
- View current addon settings
- Change addon configuration
- Test config changes before applying them

**Finding new addons:**
- Browse the entire addon store
- Search for specific addons
- Check if an addon works on your system before installing

**Debugging:**
- Read supervisor logs (super helpful when builds fail)

**System control:**
- Restart Home Assistant Core

All of this through simple conversations with your AI assistant. No clicking around in the UI.

## Contributing

Found a bug? Want a new feature? Pull requests and issues are welcome.

## License

This project follows standard open source practices. Check the repository for specific license details.

---

Built for people who'd rather chat with their AI assistant than click through menus. Works great with Kiro, Claude Desktop, and any other MCP-compatible tool.
