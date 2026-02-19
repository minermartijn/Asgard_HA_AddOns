# Home Assistant MCP Server

[![Version](https://img.shields.io/badge/version-1.8.0-blue.svg)](https://github.com/yourusername/ha-full-mcp-server)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-green.svg)](https://www.home-assistant.io/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-orange.svg)](https://modelcontextprotocol.io/)

A comprehensive Model Context Protocol (MCP) server that enables AI assistants to manage and control your entire Home Assistant installation through natural conversation.

## What is this?

This addon transforms your Home Assistant into an MCP server, allowing AI assistants like Claude, Kiro, or any MCP-compatible tool to:

- **Manage addons** - Install, configure, update, and troubleshoot
- **Control devices** - Turn on lights, adjust thermostats, trigger scenes
- **System administration** - Backups, configuration, logs, diagnostics
- **Automation** - Create, modify, and manage automations
- **Dashboards** - Build and customize Lovelace dashboards

All through simple, natural language conversations with your AI assistant.

## Features

### 🔧 Complete Addon Management (22 tools)
Install, uninstall, start, stop, restart, update, configure, and troubleshoot addons. Browse the addon store, check compatibility, rebuild custom addons, and view logs.

### 💾 Backup & Restore (5 tools)
Create full or partial backups with encryption, list and inspect backups, restore from any backup, and manage backup storage.

### 🏠 Device & Entity Control (6 tools)
List and filter entities, get current states, control any device through service calls, view entity history, and discover available services.

### 🔌 Integration Management (4 tools)
List all configured integrations, reload integrations without restarting, view integration details, and remove integrations.

### 📊 Dashboard Management (4 tools)
List all Lovelace dashboards, view and export configurations, create custom dashboards with views and cards, and delete custom dashboards.

### ⚡ Automation Management (8 tools)
Full CRUD operations for automations, enable/disable/trigger automations, view detailed configurations, and test automations.

### 🔍 System Diagnostics (10 tools)
Monitor system health (CPU, memory, disk, database), analyze error logs, find unavailable entities, track database growth, verify network connectivity, audit custom components, analyze startup performance, validate automations, scan for deprecation warnings, and get per-integration diagnostics.

### ⚙️ System Administration (6 tools)
Read and write configuration files, validate configuration before restarting, view Supervisor and Core logs, and restart Home Assistant Core.

**Total: 59 tools** across 8 categories

## Installation

### 1. Add the Repository

Add this repository to your Home Assistant addon store:

```
https://github.com/yourusername/ha-full-mcp-server
```

### 2. Install the Addon

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Find "HA Full MCP Server" in the list
3. Click **Install**

### 3. Configure

1. Go to the **Configuration** tab
2. Set your `api_key` (or leave blank to auto-generate)
3. Set your `ha_token` (long-lived access token from your profile)
4. Optionally customize which tools are enabled
5. Click **Save**

**Getting a Long-Lived Access Token:**
1. Go to your Home Assistant profile (click your name in the sidebar)
2. Scroll to **Long-Lived Access Tokens**
3. Click **Create Token**
4. Give it a name like "MCP Server"
5. Copy the token and paste it into the addon configuration

### 4. Start

1. Go to the **Info** tab
2. Click **Start**
3. Check the **Log** tab for your API key if you didn't set one

## Configuration

### Basic Configuration

```yaml
ha_token: "your_long_lived_access_token"  # Required for entity/integration tools
api_key: "your_secret_api_key"            # Authentication key (auto-generated if empty)
log_level: info                            # Logging: debug, info, warning, error
port: 8010                                 # Port number (default: 8010)
```

### Tool Toggles

Every tool can be individually enabled or disabled in the addon configuration UI. All tools are enabled by default. You can disable specific tools for security:

- Disable `uninstall_addon` to prevent accidental deletions
- Disable `restart_homeassistant` to prevent system disruptions
- Disable `delete_backup` to protect backups
- Disable `call_service` to prevent device control

## Connecting AI Assistants

### Kiro

Add to your `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://YOUR-HA-IP:8010/sse?api_key=YOUR-API-KEY",
      "transport": "sse"
    }
  }
}
```

### Claude Desktop

Claude Desktop supports remote MCP servers with OAuth:

1. Open Claude Desktop → Settings → Connectors
2. Click "Add Custom Connector"
3. Enter your Home Assistant URL: `http://YOUR-HA-IP:8010`
4. Follow the OAuth flow to authorize

### Other MCP Clients

Any MCP-compatible client can connect using the SSE transport:

- **URL**: `http://YOUR-HA-IP:8010/sse?api_key=YOUR-API-KEY`
- **Transport**: SSE (Server-Sent Events)
- **Authentication**: API key in URL parameter

## Usage Examples

Once connected, you can have natural conversations with your AI assistant:

**Addon Management:**
```
"What addons do I have installed?"
"Install the ESPHome addon"
"The Node-RED addon isn't working, check the logs"
"Update all my addons"
```

**Device Control:**
```
"Turn on the living room lights"
"What's the temperature in the bedroom?"
"Set the thermostat to 72 degrees"
"Show me all unavailable entities"
```

**System Diagnostics:**
```
"Run a full diagnostic on my Home Assistant"
"Why is my system running slow?"
"Check for deprecation warnings"
"How much disk space is my database using?"
```

**Automation:**
```
"Create an automation to turn off lights at 10pm"
"Show me all my automations"
"Disable the morning routine automation"
```

**Backups:**
```
"Create a backup before I update"
"List all my backups"
"Restore from yesterday's backup"
```

## Comparison with Native HA MCP Server

Home Assistant 2024.x includes a built-in MCP server. Here's how this addon compares:

| Feature | Native HA MCP | This Addon |
|---------|---------------|------------|
| Entity Control | ✅ Basic | ✅ Advanced |
| Addon Management | ❌ | ✅ 22 tools |
| Backup Management | ❌ | ✅ 5 tools |
| System Diagnostics | ❌ | ✅ 10 tools |
| Automation CRUD | ❌ | ✅ 8 tools |
| Dashboard Management | ❌ | ✅ 4 tools |
| Configuration Files | ❌ | ✅ Read/Write |
| Total Tools | ~10 | 59 |
| Setup | OAuth required | Simple API key |

**Use this addon if you want:**
- Complete Home Assistant management
- System administration capabilities
- Diagnostic and troubleshooting tools
- Addon and backup management
- Granular control over available tools

## Complete Tool List

**Addon Management (22 tools):**
list_addons, get_addon_info, get_addon_logs, start_addon, stop_addon, restart_addon, update_addon, install_addon, uninstall_addon, get_addon_configuration, set_addon_configuration, validate_addon_configuration, rebuild_addon, list_store_addons, reload_addons, check_addon_availability, get_supervisor_logs, get_homeassistant_logs, restart_homeassistant, read_config_file, write_config_file, check_config

**Backup Management (5 tools):**
create_backup, list_backups, get_backup_info, restore_backup, delete_backup

**Integration Management (4 tools):**
list_integrations, reload_integration, get_integration_info, remove_integration

**Entity Management (6 tools):**
list_entities, get_entity_state, set_entity_state, call_service, get_services, get_entity_history

**Dashboard Management (4 tools):**
list_dashboards, get_dashboard_config, create_dashboard, delete_dashboard

**Automation Management (8 tools):**
list_automations, get_automation, create_automation, update_automation, delete_automation, enable_automation, disable_automation, trigger_automation

**Diagnostic Tools (10 tools):**
get_system_health, get_error_log_summary, list_unavailable_entities, get_recorder_stats, check_network_connectivity, list_custom_components, get_startup_time_breakdown, validate_all_automations, list_deprecated_features, get_integration_diagnostics

## Security

### Authentication

The addon uses API key authentication. Your API key should be kept private - anyone with it can manage your Home Assistant installation.

### Tool Toggles

For security, you can disable specific tools in the addon configuration UI. This allows you to create custom security profiles:

- **Read-only mode**: Disable all control/management tools
- **Safe mode**: Disable destructive operations (uninstall, delete, remove)
- **Basic mode**: Enable only essential tools

### Network Security

- The addon listens on all interfaces by default (`0.0.0.0`)
- Use a firewall to restrict access if exposed to the internet
- Consider using a reverse proxy with additional authentication
- The API key is embedded in the URL for proxy compatibility

## Troubleshooting

### Connection Issues

**"Connection refused" or can't connect:**
- Verify the addon is running (check the Info tab)
- Confirm you're using the correct IP address and port
- Check firewall rules aren't blocking port 8010

### Authentication Errors

**"Unauthorized" errors:**
- Verify your API key matches the one in the addon logs
- Ensure there are no extra spaces when copying the key
- For entity/integration tools, confirm `ha_token` is set

### Tool Not Working

**Entity/Integration tools not working:**
- Ensure `ha_token` is configured in addon settings
- Generate a new long-lived access token if needed
- Restart the addon after setting the token

**Addon won't start:**
- Check the addon logs for specific errors
- Verify port 8010 isn't used by another service
- Try changing the port in configuration

### Getting Help

1. Check the addon logs
2. Search [existing issues](https://github.com/yourusername/ha-full-mcp-server/issues)
3. Open a [new issue](https://github.com/yourusername/ha-full-mcp-server/issues/new) with logs

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

---

**Version**: 1.8.0  
**Status**: Production Ready  
**Tested**: Home Assistant 2024.x and later

Made with ❤️ for the Home Assistant community

---
Built with ⚡ by Asgard.

### Support my caffeine addiction ☕
If these addons saved you some time (or a headache), feel free to fuel my next coding session! My code is powered by high-quality caffeine—one cup equals approximately three features and only one new bug. 😉

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/minermartijn)
