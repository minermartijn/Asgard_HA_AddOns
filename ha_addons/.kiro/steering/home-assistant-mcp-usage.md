---
inclusion: always
---

# Home Assistant MCP Server - Usage Guide

## Overview

The **Home Assistant MCP Server** is a Model Context Protocol server that provides programmatic access to Home Assistant addon management. It runs as a Home Assistant addon and exposes 17 comprehensive tools for managing the entire addon lifecycle.

## Server Information

- **Server Name**: `home-assistant` (as configured in mcp.json)
- **Addon Name**: Home Assistant KIRO MCP Server ADDON
- **Addon Slug**: `local_ha_mcp_server_addon_kiro`
- **Current Version**: 1.0.0
- **Port**: 8015 (default)
- **Transport**: SSE (Server-Sent Events)
- **Authentication**: API key in URL path (Cloudflare-compatible)

## Connection Configuration

The server is configured in `.kiro/settings/mcp.json`:

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

## Available Tools (17 Total)

### Basic Addon Management (7 tools)

1. **list_addons**
   - Lists all installed Home Assistant addons
   - No parameters required
   - Shows: name, slug, version, state, description
   - Example: `mcp_home_assistant_list_addons()`

2. **get_addon_info**
   - Get detailed information about a specific addon
   - Parameters: `addon_slug` (required)
   - Shows: version, state, boot mode, CPU/memory usage, network config
   - Example: `mcp_home_assistant_get_addon_info(addon_slug="core_ssh")`

3. **start_addon**
   - Start a stopped addon
   - Parameters: `addon_slug` (required)
   - Example: `mcp_home_assistant_start_addon(addon_slug="core_ssh")`

4. **stop_addon**
   - Stop a running addon
   - Parameters: `addon_slug` (required)
   - Example: `mcp_home_assistant_stop_addon(addon_slug="core_ssh")`

5. **restart_addon**
   - Restart an addon
   - Parameters: `addon_slug` (required)
   - Example: `mcp_home_assistant_restart_addon(addon_slug="core_ssh")`

6. **get_addon_logs**
   - Retrieve logs from an addon
   - Parameters: `addon_slug` (required)
   - Returns: Last 10,000 characters of logs
   - Example: `mcp_home_assistant_get_addon_logs(addon_slug="core_ssh")`

7. **update_addon**
   - Check for updates and update an addon
   - Parameters: `addon_slug` (required)
   - Performs: cache refresh, update check, update, start, log check
   - Example: `mcp_home_assistant_update_addon(addon_slug="core_ssh")`

### Addon Lifecycle Management (3 tools)

8. **install_addon**
   - Install an addon from the Home Assistant store
   - Parameters: 
     - `addon_slug` (required)
     - `version` (optional) - specific version to install
   - Async operation - returns immediately with job info
   - Example: `mcp_home_assistant_install_addon(addon_slug="core_git_pull")`

9. **uninstall_addon**
   - Uninstall an addon (DESTRUCTIVE)
   - Parameters:
     - `addon_slug` (required)
     - `remove_config` (optional, default: false) - whether to remove config
   - Async operation - returns immediately with job info
   - Example: `mcp_home_assistant_uninstall_addon(addon_slug="core_git_pull", remove_config=false)`

10. **rebuild_addon**
    - Rebuild a local/custom addon from source
    - Parameters: `addon_slug` (required)
    - Only works with local addons (slug starts with 'local_')
    - Async operation - may take several minutes
    - Example: `mcp_home_assistant_rebuild_addon(addon_slug="local_my_addon")`

### Addon Configuration (3 tools)

11. **get_addon_configuration**
    - Get current configuration and schema for an addon
    - Parameters: `addon_slug` (required)
    - Returns: current options, schema, available settings
    - Example: `mcp_home_assistant_get_addon_configuration(addon_slug="core_ssh")`

12. **set_addon_configuration**
    - Update addon configuration
    - Parameters:
      - `addon_slug` (required)
      - `options` (required) - JSON object with config options
      - `boot` (optional) - "auto" or "manual"
      - `network` (optional) - network configuration object
    - Shows before/after comparison
    - Requires restart to take effect
    - Example: `mcp_home_assistant_set_addon_configuration(addon_slug="core_ssh", options={"password": "newpass"})`

13. **validate_addon_configuration**
    - Validate configuration without applying it
    - Parameters:
      - `addon_slug` (required)
      - `options` (required) - JSON object to validate
    - Returns: validation results with specific errors if invalid
    - Example: `mcp_home_assistant_validate_addon_configuration(addon_slug="core_ssh", options={"password": "test"})`

### Addon Discovery (3 tools)

14. **list_store_addons**
    - List all available addons from the store
    - Parameters:
      - `repository` (optional) - filter by repository (e.g., "core", "local")
      - `search` (optional) - search query for name/description
    - Shows: name, slug, version, installation status, description
    - Grouped by repository
    - Example: `mcp_home_assistant_list_store_addons(search="git")`

15. **reload_addons**
    - Refresh the addon catalog
    - No parameters required
    - Useful after adding new repositories
    - Does not affect running addons
    - Example: `mcp_home_assistant_reload_addons()`

16. **check_addon_availability**
    - Check if an addon is compatible with your system
    - Parameters: `addon_slug` (required)
    - Shows: architecture compatibility, availability status, reasons if unavailable
    - Example: `mcp_home_assistant_check_addon_availability(addon_slug="core_git_pull")`

### System Debugging (1 tool)

17. **get_supervisor_logs**
    - Get Home Assistant Supervisor logs
    - No parameters required
    - Returns: Last 100 lines of supervisor logs
    - Automatic analysis: errors, warnings, addon activity
    - Essential for debugging addon builds and installations
    - Example: `mcp_home_assistant_get_supervisor_logs()`

### System Control (1 tool)

18. **restart_homeassistant**
    - Restart Home Assistant Core
    - No parameters required
    - Restarts Core while keeping Supervisor and addons running
    - Use after configuration changes requiring restart
    - Warning: Temporarily disconnects all clients
    - Example: `mcp_home_assistant_restart_homeassistant()`

## Common Workflows

### Installing a New Addon

```python
# 1. Search for available addons
mcp_home_assistant_list_store_addons(search="git")

# 2. Check if addon is compatible
mcp_home_assistant_check_addon_availability(addon_slug="core_git_pull")

# 3. Install the addon
mcp_home_assistant_install_addon(addon_slug="core_git_pull")

# 4. Verify installation
mcp_home_assistant_get_addon_info(addon_slug="core_git_pull")

# 5. Start if needed
mcp_home_assistant_start_addon(addon_slug="core_git_pull")
```

### Configuring an Addon

```python
# 1. Get current configuration
mcp_home_assistant_get_addon_configuration(addon_slug="core_ssh")

# 2. Validate new configuration
mcp_home_assistant_validate_addon_configuration(
    addon_slug="core_ssh",
    options={"password": "newpassword"}
)

# 3. Apply configuration
mcp_home_assistant_set_addon_configuration(
    addon_slug="core_ssh",
    options={"password": "newpassword"}
)

# 4. Restart addon for changes to take effect
mcp_home_assistant_restart_addon(addon_slug="core_ssh")
```

### Debugging Addon Issues

```python
# 1. Check addon status
mcp_home_assistant_get_addon_info(addon_slug="local_my_addon")

# 2. Check addon logs
mcp_home_assistant_get_addon_logs(addon_slug="local_my_addon")

# 3. Check supervisor logs for build/install issues
mcp_home_assistant_get_supervisor_logs()

# 4. Restart if needed
mcp_home_assistant_restart_addon(addon_slug="local_my_addon")
```

### Updating Addons

```python
# 1. Update a specific addon
mcp_home_assistant_update_addon(addon_slug="core_ssh")

# 2. For local addons, use rebuild instead
mcp_home_assistant_rebuild_addon(addon_slug="local_my_addon")

# 3. Check logs after update
mcp_home_assistant_get_addon_logs(addon_slug="core_ssh")
```

## Important Notes

### Addon Slugs

- **Core addons**: Start with `core_` (e.g., `core_ssh`, `core_mosquitto`)
- **Community addons**: Start with repository ID (e.g., `a0d7b954_vscode`)
- **Local addons**: Start with `local_` (e.g., `local_ha_mcp_server_addon_kiro`)

### Async Operations

Some operations are asynchronous and return immediately:
- `install_addon` - Installation happens in background
- `uninstall_addon` - Uninstallation happens in background
- `rebuild_addon` - Rebuild may take several minutes

Use `get_addon_info` to check status after async operations.

### Configuration Changes

Configuration changes typically require an addon restart:
```python
mcp_home_assistant_set_addon_configuration(...)
mcp_home_assistant_restart_addon(...)
```

### Supervisor Logs

The supervisor logs are essential for:
- Debugging addon build failures
- Monitoring installation progress
- Troubleshooting system-level issues
- Checking for errors during updates

## Error Handling

All tools provide comprehensive error messages with:
- Clear error descriptions
- Possible reasons for failure
- Actionable suggestions for resolution
- Troubleshooting steps

Common error types:
- **Permission errors**: Check `supervisor_api: true` in addon config
- **Not found errors**: Verify addon slug spelling
- **Validation errors**: Check configuration against schema
- **Architecture errors**: Addon not compatible with your system

## Authentication

The server uses API key authentication embedded in the URL path:
- Format: `/messages/{api_key}`
- Cloudflare-compatible (survives proxy)
- Configured in addon settings
- Generate with: `python generate_api_key.py`

## Best Practices

1. **Always check availability** before installing addons
2. **Validate configuration** before applying changes
3. **Check logs** after operations to verify success
4. **Use supervisor logs** for debugging build issues
5. **Restart addons** after configuration changes
6. **Search store** before installing to find the right addon
7. **Monitor async operations** with `get_addon_info`

## Limitations

- Local addons cannot be updated via API (must rebuild manually)
- Some operations require specific permissions
- Async operations may take time to complete
- Configuration validation depends on addon schema availability

## Support

For issues or questions:
- Check addon logs: `get_addon_logs`
- Check supervisor logs: `get_supervisor_logs`
- Verify addon status: `get_addon_info`
- Review configuration: `get_addon_configuration`

## Version History

- **1.1.0** (2026-02-14): Added restart Home Assistant tool
- **1.0.0** (2026-02-14): Production release with 17 tools and custom icon
- **0.9.0** (2026-02-14): Added supervisor logs tool
- **0.8.0** (2026-02-14): Added store discovery tools
- **0.7.0** (2026-02-14): Added configuration and lifecycle tools
- **0.6.0** (2026-02-13): Initial release with basic management tools
