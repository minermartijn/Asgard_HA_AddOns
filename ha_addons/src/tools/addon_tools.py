"""Addon management tools for Home Assistant MCP Server."""
import asyncio
import logging
from typing import Any
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)


def get_addon_tool_definitions() -> list[Tool]:
    """Return all addon-related tool definitions."""
    return [
        Tool(
            name="list_addons",
            description="List all installed Home Assistant addons/apps with their status and details",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_addon_info",
            description="Get detailed information about a specific addon",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon (e.g., 'core_ssh', 'a0d7b954_vscode')",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="start_addon",
            description="Start a stopped addon",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to start",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="stop_addon",
            description="Stop a running addon",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to stop",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="restart_addon",
            description="Restart an addon",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to restart",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="get_addon_logs",
            description="Get the logs from an addon",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="update_addon",
            description="Check for updates and update an addon. This tool will: 1) Refresh update cache, 2) Check if update is available, 3) Update if available, 4) Start the addon, 5) Check logs for errors",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to update",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="install_addon",
            description="Install an addon from the Home Assistant add-on store. This tool installs add-ons by their slug identifier. The installation happens asynchronously - the tool returns immediately with job information while the installation continues in the background. Use get_addon_info to check installation status afterwards. Requires appropriate permissions to install add-ons.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to install (e.g., 'core_ssh', 'a0d7b954_vscode', 'core_mosquitto'). This must be a valid addon slug from the Home Assistant add-on store.",
                    },
                    "version": {
                        "type": "string",
                        "description": "Optional specific version to install (e.g., '9.7.1', '1.2.0'). If not specified, the latest available version will be installed.",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="uninstall_addon",
            description="⚠️ DESTRUCTIVE OPERATION: Uninstall an addon from Home Assistant. This permanently removes the addon and optionally its configuration data. The uninstallation happens asynchronously - the tool returns immediately with job information while the uninstallation continues in the background. Use get_addon_info to verify removal. WARNING: This action cannot be undone. All addon data will be lost unless you have backups.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to uninstall (e.g., 'core_ssh', 'a0d7b954_vscode'). The addon must be stopped before uninstallation.",
                    },
                    "remove_config": {
                        "type": "boolean",
                        "description": "Optional: If true, removes addon configuration data. If false or not specified, configuration is preserved for potential reinstallation. Default: false (keep config).",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="get_addon_configuration",
            description="Get the current configuration options and schema for an addon. Returns the addon's configuration settings, available options schema, and whether the addon has configurable options. Use this to view current settings before making changes with set_addon_configuration.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to get configuration for (e.g., 'core_ssh', 'a0d7b954_vscode')",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="set_addon_configuration",
            description="Set or update configuration options for an addon. This tool allows you to modify addon settings, boot mode, and network configuration. Configuration changes typically require an addon restart to take effect. The tool validates options against the addon's schema and provides before/after comparison.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to configure (e.g., 'core_ssh', 'a0d7b954_vscode')",
                    },
                    "options": {
                        "type": "object",
                        "description": "Configuration options to set as a JSON object. The structure depends on the addon's schema. Use get_addon_configuration to see available options and current values.",
                    },
                    "boot": {
                        "type": "string",
                        "description": "Optional boot mode: 'auto' (start automatically) or 'manual' (start manually). If not specified, boot mode remains unchanged.",
                        "enum": ["auto", "manual"],
                    },
                    "network": {
                        "type": "object",
                        "description": "Optional network configuration as a JSON object. Structure depends on addon requirements.",
                    },
                },
                "required": ["addon_slug", "options"],
            },
        ),
        Tool(
            name="validate_addon_configuration",
            description="Validate configuration options for an addon without applying them. This tool checks if the provided configuration is valid according to the addon's schema, helping you test configuration before committing changes. Returns detailed validation results including specific errors if validation fails. Use this before set_addon_configuration to ensure your configuration is correct.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to validate configuration for (e.g., 'core_ssh', 'a0d7b954_vscode')",
                    },
                    "options": {
                        "type": "object",
                        "description": "Configuration options to validate as a JSON object. The structure should match the addon's schema. Use get_addon_configuration to see the expected structure.",
                    },
                },
                "required": ["addon_slug", "options"],
            },
        ),
        Tool(
            name="rebuild_addon",
            description="Rebuild a local or custom addon from source. This tool rebuilds addons that have been modified or need to be recompiled. Only works with local/custom addons, not store addons. The rebuild process happens asynchronously and may take several minutes. Use this when: 1) Developing custom addons, 2) Addon source code has been modified, 3) Addon needs recompilation after system updates. Note: Store addons cannot be rebuilt - use update_addon instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the local/custom addon to rebuild (e.g., 'local_my_addon'). Must be a local or custom addon, not a store addon.",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="list_store_addons",
            description="List all available addons from the Home Assistant add-on store. This tool shows addons that can be installed, including their descriptions, versions, and installation status. Useful for discovering new addons or checking what's available before installation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Optional repository filter (e.g., 'core', 'local'). If specified, only shows addons from that repository.",
                    },
                    "search": {
                        "type": "string",
                        "description": "Optional search query to filter addons by name, description, or slug. Case-insensitive partial matching.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="reload_addons",
            description="Reload the addon list to refresh available addons. This is useful after adding a new repository or when the addon list needs to be refreshed without restarting Home Assistant. The operation is quick and does not affect running addons.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="check_addon_availability",
            description="Check if a specific addon is available for installation on this system. This verifies architecture compatibility, dependencies, and other requirements. Useful before attempting to install an addon to understand why it might not be available.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to check availability for (e.g., 'core_ssh', 'a0d7b954_vscode')",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="get_supervisor_logs",
            description="Get logs from the Home Assistant Supervisor. This is essential for debugging addon builds, installation issues, and system-level problems. Shows supervisor operations including addon installations, builds, updates, and system events.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="restart_homeassistant",
            description="Restart Home Assistant Core. This restarts the Home Assistant Core service while keeping the Supervisor and addons running. Use this after configuration changes that require a restart. Note: This will temporarily disconnect all clients and integrations.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


async def handle_addon_tool(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle addon tool execution."""
    try:
        if name == "list_addons":
            addons = await ha_client.list_addons()
            
            # Format addon information
            result = "# Home Assistant Addons\n\n"
            for addon in addons:
                result += f"## {addon.get('name', 'Unknown')}\n"
                result += f"- **Slug**: {addon.get('slug', 'N/A')}\n"
                result += f"- **Version**: {addon.get('version', 'N/A')}\n"
                result += f"- **State**: {addon.get('state', 'N/A')}\n"
                result += f"- **Description**: {addon.get('description', 'No description')}\n"
                result += f"- **Installed**: {addon.get('installed', 'N/A')}\n"
                result += "\n"
            
            if not addons:
                result = "No addons found."
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_addon_info":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            info = await ha_client.get_addon_info(addon_slug)
            
            # Format detailed addon info
            result = f"# {info.get('name', 'Unknown Addon')}\n\n"
            result += f"**Slug**: {info.get('slug', 'N/A')}\n"
            result += f"**Version**: {info.get('version', 'N/A')}\n"
            result += f"**State**: {info.get('state', 'N/A')}\n"
            result += f"**Description**: {info.get('description', 'No description')}\n\n"
            result += f"**Auto Update**: {info.get('auto_update', 'N/A')}\n"
            result += f"**Boot**: {info.get('boot', 'N/A')}\n"
            result += f"**CPU Percent**: {info.get('cpu_percent', 'N/A')}\n"
            result += f"**Memory Percent**: {info.get('memory_percent', 'N/A')}\n"
            result += f"**Network**: {info.get('network', 'N/A')}\n"
            
            if info.get('changelog'):
                result += f"\n## Changelog\n{info.get('changelog')}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "start_addon":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            await ha_client.start_addon(addon_slug)
            return [TextContent(type="text", text=f"✓ Started addon: {addon_slug}")]
        
        elif name == "stop_addon":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            await ha_client.stop_addon(addon_slug)
            return [TextContent(type="text", text=f"✓ Stopped addon: {addon_slug}")]
        
        elif name == "restart_addon":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            await ha_client.restart_addon(addon_slug)
            return [TextContent(type="text", text=f"✓ Restarted addon: {addon_slug}")]
        
        elif name == "get_addon_logs":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            logs = await ha_client.get_addon_logs(addon_slug)
            
            # Truncate logs if too long
            max_length = 10000
            if len(logs) > max_length:
                logs = logs[-max_length:] + f"\n\n... (showing last {max_length} characters)"
            
            result = f"# Logs for {addon_slug}\n\n```\n{logs}\n```"
            return [TextContent(type="text", text=result)]
        
        elif name == "update_addon":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            result = f"# Updating Addon: {addon_slug}\n\n"
            
            # Step 1: Refresh updates cache
            result += "## Step 1: Refreshing update cache...\n"
            try:
                await ha_client.refresh_updates()
                result += "✓ Update cache refreshed\n\n"
            except Exception as e:
                result += f"⚠ Warning: Could not refresh update cache: {e}\n\n"
            
            # Step 2: Check for updates
            result += "## Step 2: Checking for updates...\n"
            try:
                update_info = await ha_client.check_addon_update(addon_slug)
                current_ver = update_info.get("current_version", "unknown")
                latest_ver = update_info.get("latest_version", "unknown")
                update_available = update_info.get("update_available", False)
                addon_name = update_info.get("name", addon_slug)
                
                result += f"- Addon: {addon_name}\n"
                result += f"- Current Version: {current_ver}\n"
                result += f"- Latest Version: {latest_ver}\n"
                result += f"- Update Available: {'Yes' if update_available else 'No'}\n\n"
                
                if not update_available:
                    result += "ℹ️ No update available. Addon is already at the latest version.\n"
                    return [TextContent(type="text", text=result)]
            except Exception as e:
                result += f"❌ Error checking for updates: {e}\n"
                return [TextContent(type="text", text=result)]
            
            # Step 3: Perform update
            result += "## Step 3: Updating addon...\n"
            try:
                await ha_client.update_addon(addon_slug)
                result += f"✓ Update initiated: {current_ver} → {latest_ver}\n"
                result += "⏳ Waiting for update to complete...\n\n"
                
                # Wait a bit for update to settle
                await asyncio.sleep(5)
            except Exception as e:
                result += f"❌ Update failed: {e}\n"
                return [TextContent(type="text", text=result)]
            
            # Step 4: Start the addon
            result += "## Step 4: Starting addon...\n"
            try:
                await ha_client.start_addon(addon_slug)
                result += f"✓ Addon started\n"
                
                # Wait for startup
                await asyncio.sleep(3)
            except Exception as e:
                result += f"⚠ Warning: Could not start addon: {e}\n"
            
            # Step 5: Check logs for errors
            result += "\n## Step 5: Checking logs for errors...\n"
            try:
                logs = await ha_client.get_addon_logs(addon_slug)
                
                # Get last 20 lines
                log_lines = logs.strip().split('\n')
                recent_logs = log_lines[-20:] if len(log_lines) > 20 else log_lines
                
                # Check for common error patterns
                error_patterns = ["error", "failed", "exception", "fatal", "critical"]
                errors_found = []
                for line in recent_logs:
                    if any(pattern in line.lower() for pattern in error_patterns):
                        errors_found.append(line)
                
                if errors_found:
                    result += "⚠ Potential errors found in logs:\n```\n"
                    result += "\n".join(errors_found[-10:])  # Last 10 errors
                    result += "\n```\n"
                else:
                    result += "✓ No obvious errors in recent logs\n"
                
                result += "\n### Recent Log Output:\n```\n"
                result += "\n".join(recent_logs)
                result += "\n```\n"
                
            except Exception as e:
                result += f"⚠ Could not retrieve logs: {e}\n"
            
            # Final summary
            result += f"\n## Summary\n"
            result += f"✓ Update completed: {addon_name} updated from {current_ver} to {latest_ver}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "install_addon":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            version = arguments.get("version")
            
            result = f"# Installing Addon: {addon_slug}\n\n"
            
            # Validate addon_slug format (basic check)
            if not addon_slug or not isinstance(addon_slug, str):
                return [TextContent(type="text", text="Error: Invalid addon_slug format")]
            
            # Attempt installation
            try:
                install_result = await ha_client.install_addon(addon_slug, version)
                
                result += "## Installation Initiated\n"
                result += f"- **Addon**: {addon_slug}\n"
                if version:
                    result += f"- **Version**: {version}\n"
                else:
                    result += f"- **Version**: Latest available\n"
                result += f"- **Status**: {install_result.get('result', 'unknown')}\n"
                
                if install_result.get('job_id'):
                    result += f"- **Job ID**: {install_result['job_id']}\n"
                
                result += "\n⏳ **Installation Progress**\n"
                result += "The installation is running in the background. This may take several minutes depending on the addon size and your system.\n\n"
                
                # Wait a bit to allow installation to start
                result += "Waiting for installation to begin...\n"
                await asyncio.sleep(3)
                
                # Check if addon appears in the list
                try:
                    addon_info = await ha_client.get_addon_info(addon_slug)
                    addon_state = addon_info.get('state', 'unknown')
                    addon_name = addon_info.get('name', addon_slug)
                    
                    result += f"\n## Current Status\n"
                    result += f"- **Name**: {addon_name}\n"
                    result += f"- **State**: {addon_state}\n"
                    
                    if addon_state == "started":
                        result += "\n✓ **Installation Complete**: Addon is installed and running\n"
                    elif addon_state == "stopped":
                        result += "\n✓ **Installation Complete**: Addon is installed but not started\n"
                        result += "\nℹ️ Use `start_addon` to start the addon if needed.\n"
                    else:
                        result += f"\n⏳ **Installation in Progress**: Current state is '{addon_state}'\n"
                        result += "\nℹ️ Use `get_addon_info` to check installation status.\n"
                    
                except Exception as check_error:
                    result += f"\n⏳ **Installation in Progress**\n"
                    result += f"Could not verify status yet: {check_error}\n"
                    result += "\nℹ️ Use `get_addon_info` to check installation status once complete.\n"
                
                # Success confirmation
                result += f"\n## Next Steps\n"
                result += f"1. Monitor installation: `get_addon_info {addon_slug}`\n"
                result += f"2. View logs: `get_addon_logs {addon_slug}`\n"
                result += f"3. Start addon (if needed): `start_addon {addon_slug}`\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                # Addon not found or invalid request
                result += f"## Installation Failed\n"
                result += f"❌ **Error**: {str(ve)}\n\n"
                result += "**Possible reasons:**\n"
                result += "- Addon slug is incorrect or doesn't exist in the store\n"
                result += "- Addon is not compatible with your system architecture\n"
                result += "- Version specified is not available\n\n"
                result += "**Suggestions:**\n"
                result += "- Use `list_store_addons` to find available addons (when implemented)\n"
                result += "- Check the addon slug spelling\n"
                result += "- Verify the addon is compatible with your Home Assistant version\n"
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                # Insufficient permissions
                result += f"## Installation Failed\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                # Other errors
                result += f"## Installation Failed\n"
                result += f"❌ **Unexpected Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify network connectivity\n"
                result += "- Ensure sufficient disk space\n"
                result += "- Try again in a few moments\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "uninstall_addon":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            remove_config = arguments.get("remove_config", False)
            
            result = f"# Uninstalling Addon: {addon_slug}\n\n"
            
            # Validate addon_slug format (basic check)
            if not addon_slug or not isinstance(addon_slug, str):
                return [TextContent(type="text", text="Error: Invalid addon_slug format")]
            
            # Warning about destructive operation
            result += "⚠️ **WARNING: DESTRUCTIVE OPERATION**\n\n"
            result += "This will permanently remove the addon from your Home Assistant installation.\n"
            if remove_config:
                result += "**Configuration data will also be removed** (cannot be recovered).\n"
            else:
                result += "Configuration data will be preserved for potential reinstallation.\n"
            result += "\n"
            
            # Get addon info before uninstalling
            result += "## Step 1: Checking addon status...\n"
            try:
                addon_info = await ha_client.get_addon_info(addon_slug)
                addon_name = addon_info.get('name', addon_slug)
                addon_state = addon_info.get('state', 'unknown')
                addon_version = addon_info.get('version', 'unknown')
                
                result += f"- **Name**: {addon_name}\n"
                result += f"- **Version**: {addon_version}\n"
                result += f"- **State**: {addon_state}\n\n"
                
                # Check if addon is running
                if addon_state == "started":
                    result += "⚠️ **Addon is currently running**\n"
                    result += "Stopping addon before uninstallation...\n\n"
                    try:
                        await ha_client.stop_addon(addon_slug)
                        result += "✓ Addon stopped successfully\n\n"
                        await asyncio.sleep(2)  # Wait for stop to complete
                    except Exception as stop_error:
                        result += f"⚠️ Warning: Could not stop addon: {stop_error}\n"
                        result += "Proceeding with uninstallation anyway...\n\n"
                
            except Exception as info_error:
                result += f"⚠️ Could not retrieve addon info: {info_error}\n"
                result += "Proceeding with uninstallation...\n\n"
                addon_name = addon_slug
            
            # Attempt uninstallation
            result += "## Step 2: Uninstalling addon...\n"
            try:
                uninstall_result = await ha_client.uninstall_addon(addon_slug)
                
                result += f"✓ Uninstallation initiated for {addon_name}\n"
                result += f"- **Status**: {uninstall_result.get('result', 'unknown')}\n"
                
                if uninstall_result.get('job_id'):
                    result += f"- **Job ID**: {uninstall_result['job_id']}\n"
                
                result += "\n⏳ **Uninstallation Progress**\n"
                result += "The uninstallation is running in the background. This may take a few moments.\n\n"
                
                # Wait a bit to allow uninstallation to progress
                result += "Waiting for uninstallation to complete...\n"
                await asyncio.sleep(3)
                
                # Verify addon is removed
                result += "\n## Step 3: Verifying removal...\n"
                try:
                    # Try to get addon info - should fail if uninstalled
                    await ha_client.get_addon_info(addon_slug)
                    result += "⏳ **Uninstallation in Progress**\n"
                    result += f"Addon still appears in the system. The uninstallation may still be processing.\n"
                    result += f"\nℹ️ Use `get_addon_info {addon_slug}` to check if removal is complete.\n"
                except ValueError:
                    # Addon not found - successfully uninstalled
                    result += "✅ **Uninstallation Complete**\n"
                    result += f"Addon '{addon_name}' has been successfully removed from your system.\n"
                except Exception as verify_error:
                    result += f"⏳ **Verification Status**: {verify_error}\n"
                    result += f"\nℹ️ Use `list_addons` to verify the addon is no longer installed.\n"
                
                # Final summary
                result += f"\n## Summary\n"
                result += f"✓ Uninstallation completed for: {addon_name}\n"
                if remove_config:
                    result += "✓ Configuration data removed\n"
                else:
                    result += "ℹ️ Configuration data preserved (can be removed manually if needed)\n"
                
                result += f"\n**Note**: If you want to reinstall this addon later, use:\n"
                result += f"```\ninstall_addon {addon_slug}\n```\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                # Addon not found or not installed
                result += f"## Uninstallation Failed\n"
                result += f"❌ **Error**: {str(ve)}\n\n"
                result += "**Possible reasons:**\n"
                result += "- Addon is not installed\n"
                result += "- Addon slug is incorrect\n"
                result += "- Addon has already been uninstalled\n\n"
                result += "**Suggestions:**\n"
                result += "- Use `list_addons` to see installed addons\n"
                result += "- Verify the addon slug spelling\n"
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                # Insufficient permissions
                result += f"## Uninstallation Failed\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                # Other errors
                result += f"## Uninstallation Failed\n"
                result += f"❌ **Unexpected Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check if the addon is in use by other services\n"
                result += "- Verify the addon is stopped before uninstalling\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Try stopping the addon first: `stop_addon {addon_slug}`\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "get_addon_configuration":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            try:
                config = await ha_client.get_addon_configuration(addon_slug)
                
                result = f"# Configuration for {config.get('addon_name', addon_slug)}\n\n"
                result += f"**Addon Slug**: {config.get('addon_slug')}\n"
                result += f"**Has Configuration**: {'Yes' if config.get('has_configuration') else 'No'}\n\n"
                
                if not config.get('has_configuration'):
                    result += "ℹ️ This addon does not have configurable options.\n"
                    return [TextContent(type="text", text=result)]
                
                # Display current options
                options = config.get('options', {})
                if options:
                    result += "## Current Configuration\n\n"
                    result += "```json\n"
                    import json
                    result += json.dumps(options, indent=2)
                    result += "\n```\n\n"
                else:
                    result += "## Current Configuration\n\n"
                    result += "No options currently set (using defaults).\n\n"
                
                # Display schema if available
                schema = config.get('schema', {})
                if schema:
                    result += "## Available Options (Schema)\n\n"
                    result += "The following options can be configured:\n\n"
                    
                    # Parse schema to show available options
                    if isinstance(schema, dict):
                        for key, value in schema.items():
                            result += f"### `{key}`\n"
                            
                            if isinstance(value, dict):
                                # Show type if available
                                if 'type' in value:
                                    result += f"- **Type**: {value['type']}\n"
                                
                                # Show description if available
                                if 'description' in value:
                                    result += f"- **Description**: {value['description']}\n"
                                
                                # Show default if available
                                if 'default' in value:
                                    result += f"- **Default**: `{value['default']}`\n"
                                
                                # Show required status
                                if 'required' in value:
                                    result += f"- **Required**: {value['required']}\n"
                                
                                # Show enum values if available
                                if 'enum' in value:
                                    result += f"- **Allowed values**: {', '.join(map(str, value['enum']))}\n"
                            else:
                                result += f"- **Type**: {value}\n"
                            
                            result += "\n"
                    else:
                        result += "```json\n"
                        result += json.dumps(schema, indent=2)
                        result += "\n```\n\n"
                
                result += "## Usage\n\n"
                result += f"To update configuration, use:\n"
                result += f"```\nset_addon_configuration {addon_slug} {{'option_name': 'value'}}\n```\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                return [TextContent(type="text", text=f"Error: {str(ve)}")]
            except PermissionError as pe:
                return [TextContent(type="text", text=f"Permission Error: {str(pe)}")]
            except Exception as e:
                logger.error(f"Error getting addon configuration: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        elif name == "set_addon_configuration":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            options = arguments.get("options")
            if options is None:
                return [TextContent(type="text", text="Error: options parameter is required")]
            
            if not isinstance(options, dict):
                return [TextContent(type="text", text="Error: options must be a JSON object/dictionary")]
            
            boot = arguments.get("boot")
            network = arguments.get("network")
            
            try:
                result = f"# Updating Configuration for {addon_slug}\n\n"
                
                # Get current configuration for comparison
                result += "## Step 1: Getting current configuration...\n"
                try:
                    current_config = await ha_client.get_addon_configuration(addon_slug)
                    current_options = current_config.get('options', {})
                    addon_name = current_config.get('addon_name', addon_slug)
                    
                    result += f"✓ Current configuration retrieved for {addon_name}\n\n"
                    
                    # Show current values
                    if current_options:
                        result += "### Current Options:\n```json\n"
                        import json
                        result += json.dumps(current_options, indent=2)
                        result += "\n```\n\n"
                except Exception as e:
                    result += f"⚠ Could not retrieve current configuration: {e}\n\n"
                    addon_name = addon_slug
                
                # Show what will be changed
                result += "## Step 2: Applying new configuration...\n"
                result += "### New Options:\n```json\n"
                import json
                result += json.dumps(options, indent=2)
                result += "\n```\n"
                
                if boot:
                    result += f"\n**Boot Mode**: {boot}\n"
                if network:
                    result += f"\n**Network Configuration**: {json.dumps(network, indent=2)}\n"
                
                result += "\n"
                
                # Apply the configuration
                update_result = await ha_client.set_addon_configuration(
                    addon_slug, options, boot, network
                )
                
                result += f"✓ Configuration updated successfully\n\n"
                
                # Get updated configuration
                result += "## Step 3: Verifying changes...\n"
                try:
                    await asyncio.sleep(1)  # Brief wait for changes to apply
                    new_config = await ha_client.get_addon_configuration(addon_slug)
                    new_options = new_config.get('options', {})
                    
                    result += "### Updated Options:\n```json\n"
                    result += json.dumps(new_options, indent=2)
                    result += "\n```\n\n"
                    
                    # Show what changed
                    if current_options:
                        result += "### Changes Applied:\n"
                        for key, value in options.items():
                            old_value = current_options.get(key, "(not set)")
                            result += f"- `{key}`: `{old_value}` → `{value}`\n"
                        result += "\n"
                    
                except Exception as e:
                    result += f"⚠ Could not verify changes: {e}\n\n"
                
                # Restart recommendation
                result += "## Important Notes\n\n"
                result += "⚠️ **Configuration changes typically require an addon restart to take effect.**\n\n"
                result += "### Recommended Next Steps:\n"
                result += f"1. Restart the addon: `restart_addon {addon_slug}`\n"
                result += f"2. Check logs for any errors: `get_addon_logs {addon_slug}`\n"
                result += f"3. Verify addon is running: `get_addon_info {addon_slug}`\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                result = f"# Configuration Update Failed\n\n"
                result += f"❌ **Validation Error**: {str(ve)}\n\n"
                result += "**Possible reasons:**\n"
                result += "- Invalid option names or values\n"
                result += "- Options don't match the addon's schema\n"
                result += "- Required options are missing\n"
                result += "- Value types are incorrect (e.g., string instead of number)\n\n"
                result += "**Suggestions:**\n"
                result += f"- Use `get_addon_configuration {addon_slug}` to see available options and schema\n"
                result += "- Check the addon's documentation for valid configuration values\n"
                result += "- Ensure all required options are provided\n"
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = f"# Configuration Update Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = f"# Configuration Update Failed\n\n"
                result += f"❌ **Unexpected Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify the addon is installed and accessible\n"
                result += "- Try getting current configuration first to verify access\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "validate_addon_configuration":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            options = arguments.get("options")
            if options is None:
                return [TextContent(type="text", text="Error: options parameter is required")]
            
            if not isinstance(options, dict):
                return [TextContent(type="text", text="Error: options must be a JSON object/dictionary")]
            
            try:
                result = f"# Validating Configuration for {addon_slug}\n\n"
                
                # Show what we're validating
                result += "## Configuration to Validate\n\n"
                result += "```json\n"
                import json
                result += json.dumps(options, indent=2)
                result += "\n```\n\n"
                
                # Perform validation
                result += "## Validation Results\n\n"
                validation_result = await ha_client.validate_addon_configuration(addon_slug, options)
                
                if validation_result.get("valid"):
                    # Validation passed
                    result += "✅ **Configuration is Valid**\n\n"
                    result += "The provided configuration passes all validation checks and can be safely applied.\n\n"
                    
                    # Get current configuration to show what would change
                    try:
                        current_config = await ha_client.get_addon_configuration(addon_slug)
                        current_options = current_config.get('options', {})
                        addon_name = current_config.get('addon_name', addon_slug)
                        
                        result += f"### Addon: {addon_name}\n\n"
                        
                        # Show what would change
                        if current_options:
                            result += "### Changes that would be applied:\n"
                            changes_found = False
                            for key, new_value in options.items():
                                old_value = current_options.get(key, "(not set)")
                                if old_value != new_value:
                                    result += f"- `{key}`: `{old_value}` → `{new_value}`\n"
                                    changes_found = True
                                else:
                                    result += f"- `{key}`: `{new_value}` (unchanged)\n"
                            
                            if not changes_found:
                                result += "\nℹ️ No changes detected - all values match current configuration.\n"
                            result += "\n"
                        else:
                            result += "### New configuration values:\n"
                            for key, value in options.items():
                                result += f"- `{key}`: `{value}`\n"
                            result += "\n"
                    except Exception as e:
                        result += f"⚠ Could not retrieve current configuration for comparison: {e}\n\n"
                    
                    # Next steps
                    result += "## Next Steps\n\n"
                    result += "To apply this configuration:\n"
                    result += f"```\nset_addon_configuration {addon_slug} {json.dumps(options)}\n```\n\n"
                    result += "**Remember**: Configuration changes typically require an addon restart to take effect.\n"
                    
                else:
                    # Validation failed
                    result += "❌ **Configuration is Invalid**\n\n"
                    result += "The provided configuration has validation errors and cannot be applied.\n\n"
                    
                    # Show validation errors
                    errors = validation_result.get("errors", [])
                    if errors:
                        result += "### Validation Errors:\n\n"
                        for i, error in enumerate(errors, 1):
                            result += f"{i}. {error}\n"
                        result += "\n"
                    
                    # Provide suggestions
                    result += "## Troubleshooting Suggestions\n\n"
                    result += "**Common issues:**\n"
                    result += "- **Wrong data type**: Ensure values match expected types (string, number, boolean, etc.)\n"
                    result += "- **Missing required fields**: Check if all required options are provided\n"
                    result += "- **Invalid values**: Verify values are within allowed ranges or enum values\n"
                    result += "- **Unknown options**: Make sure option names match the addon's schema\n\n"
                    
                    result += "**How to fix:**\n"
                    result += f"1. Check the addon's schema: `get_addon_configuration {addon_slug}`\n"
                    result += "2. Review the validation errors above\n"
                    result += "3. Correct the configuration and validate again\n"
                    result += "4. Consult the addon's documentation for valid configuration examples\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                result = f"# Validation Failed\n\n"
                result += f"❌ **Error**: {str(ve)}\n\n"
                result += "**Possible reasons:**\n"
                result += "- Addon not found or invalid addon slug\n"
                result += "- Addon does not support configuration validation\n"
                result += "- Invalid options format\n\n"
                result += "**Suggestions:**\n"
                result += f"- Verify the addon exists: `get_addon_info {addon_slug}`\n"
                result += f"- Check available options: `get_addon_configuration {addon_slug}`\n"
                result += "- Ensure options is a valid JSON object\n"
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = f"# Validation Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = f"# Validation Failed\n\n"
                result += f"❌ **Unexpected Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify the addon is installed and accessible\n"
                result += "- Ensure the validation endpoint is supported by this addon\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "rebuild_addon":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            try:
                result = f"# Rebuilding Addon: {addon_slug}\n\n"
                
                # Get addon info before rebuilding
                result += "## Step 1: Checking addon status...\n"
                try:
                    addon_info = await ha_client.get_addon_info(addon_slug)
                    addon_name = addon_info.get('name', addon_slug)
                    addon_version = addon_info.get('version', 'unknown')
                    addon_state = addon_info.get('state', 'unknown')
                    
                    result += f"- **Name**: {addon_name}\n"
                    result += f"- **Version**: {addon_version}\n"
                    result += f"- **State**: {addon_state}\n\n"
                    
                    # Check if it's a local addon
                    if not addon_slug.startswith('local_'):
                        result += "⚠️ **Warning**: This appears to be a store addon.\n"
                        result += "Only local/custom addons can be rebuilt. Store addons should use `update_addon` instead.\n\n"
                except Exception as info_error:
                    result += f"⚠️ Could not retrieve addon info: {info_error}\n"
                    result += "Proceeding with rebuild attempt...\n\n"
                    addon_name = addon_slug
                
                # Attempt rebuild
                result += "## Step 2: Initiating rebuild...\n"
                rebuild_result = await ha_client.rebuild_addon(addon_slug)
                
                result += f"✓ Rebuild initiated for {addon_name}\n"
                result += f"- **Status**: {rebuild_result.get('result', 'unknown')}\n"
                
                if rebuild_result.get('job_id'):
                    result += f"- **Job ID**: {rebuild_result['job_id']}\n"
                
                result += "\n⏳ **Rebuild Progress**\n"
                result += "The rebuild is running in the background. This may take several minutes depending on the addon complexity.\n\n"
                
                # Wait for rebuild to start
                result += "Waiting for rebuild to begin...\n"
                await asyncio.sleep(5)
                
                # Check addon status
                result += "\n## Step 3: Checking rebuild status...\n"
                try:
                    updated_info = await ha_client.get_addon_info(addon_slug)
                    updated_state = updated_info.get('state', 'unknown')
                    
                    result += f"- **Current State**: {updated_state}\n"
                    
                    if updated_state == "started":
                        result += "\n✓ **Rebuild appears successful** - Addon is running\n"
                    elif updated_state == "stopped":
                        result += "\n⏳ **Rebuild in progress or completed** - Addon is stopped\n"
                        result += "You may need to start the addon after rebuild completes.\n"
                    else:
                        result += f"\n⏳ **Rebuild status**: {updated_state}\n"
                    
                except Exception as check_error:
                    result += f"⚠️ Could not check status: {check_error}\n"
                
                # Try to get logs
                result += "\n## Step 4: Checking build logs...\n"
                try:
                    logs = await ha_client.get_addon_logs(addon_slug)
                    
                    # Get last 30 lines
                    log_lines = logs.strip().split('\n')
                    recent_logs = log_lines[-30:] if len(log_lines) > 30 else log_lines
                    
                    # Check for build-related messages
                    build_messages = []
                    for line in recent_logs:
                        if any(keyword in line.lower() for keyword in ['build', 'rebuild', 'compil', 'docker', 'image']):
                            build_messages.append(line)
                    
                    if build_messages:
                        result += "### Build-related log entries:\n```\n"
                        result += "\n".join(build_messages[-15:])  # Last 15 build messages
                        result += "\n```\n\n"
                    
                    # Check for errors
                    error_patterns = ["error", "failed", "exception", "fatal"]
                    errors_found = []
                    for line in recent_logs:
                        if any(pattern in line.lower() for pattern in error_patterns):
                            errors_found.append(line)
                    
                    if errors_found:
                        result += "⚠️ **Potential errors found in logs:**\n```\n"
                        result += "\n".join(errors_found[-10:])  # Last 10 errors
                        result += "\n```\n\n"
                    else:
                        result += "✓ No obvious errors in recent logs\n\n"
                    
                except Exception as log_error:
                    result += f"⚠️ Could not retrieve logs: {log_error}\n\n"
                
                # Final summary
                result += "## Summary\n\n"
                result += f"✓ Rebuild initiated for: {addon_name}\n"
                result += f"- The rebuild process is running in the background\n"
                result += f"- Monitor progress with: `get_addon_logs {addon_slug}`\n"
                result += f"- Check status with: `get_addon_info {addon_slug}`\n\n"
                
                result += "### Next Steps:\n"
                result += f"1. Wait for rebuild to complete (may take 5-15 minutes)\n"
                result += f"2. Check logs: `get_addon_logs {addon_slug}`\n"
                result += f"3. Start addon if needed: `start_addon {addon_slug}`\n"
                result += f"4. Verify functionality after rebuild\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                result = f"# Rebuild Failed\n\n"
                result += f"❌ **Error**: {str(ve)}\n\n"
                result += "**Possible reasons:**\n"
                result += "- Addon is not a local/custom addon\n"
                result += "- Store addons cannot be rebuilt (use `update_addon` instead)\n"
                result += "- Addon slug is incorrect\n"
                result += "- Addon does not support rebuilding\n\n"
                result += "**Suggestions:**\n"
                result += "- Verify this is a local addon (slug usually starts with 'local_')\n"
                result += "- For store addons, use `update_addon` to get the latest version\n"
                result += "- Check addon exists: `get_addon_info {addon_slug}`\n"
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = f"# Rebuild Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = f"# Rebuild Failed\n\n"
                result += f"❌ **Unexpected Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify the addon source code is valid\n"
                result += "- Ensure sufficient disk space for build\n"
                result += "- Try stopping the addon first: `stop_addon {addon_slug}`\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "list_store_addons":
            repository = arguments.get("repository")
            search = arguments.get("search")
            
            try:
                result = "# Home Assistant Add-on Store\n\n"
                
                # Add filter information
                if repository or search:
                    result += "## Filters Applied\n"
                    if repository:
                        result += f"- **Repository**: {repository}\n"
                    if search:
                        result += f"- **Search**: {search}\n"
                    result += "\n"
                
                # Get store addons
                addons = await ha_client.list_store_addons(repository, search)
                
                if not addons:
                    result += "No addons found matching the criteria.\n\n"
                    result += "**Suggestions:**\n"
                    result += "- Try a different search term\n"
                    result += "- Remove filters to see all available addons\n"
                    result += "- Check if repositories are properly configured\n"
                    return [TextContent(type="text", text=result)]
                
                result += f"## Available Add-ons ({len(addons)} found)\n\n"
                
                # Group by repository for better organization
                repos = {}
                for addon in addons:
                    repo = addon.get('repository', 'unknown')
                    if repo not in repos:
                        repos[repo] = []
                    repos[repo].append(addon)
                
                # Display addons grouped by repository
                for repo, repo_addons in sorted(repos.items()):
                    result += f"### Repository: {repo}\n\n"
                    
                    for addon in repo_addons:
                        name = addon.get('name', 'Unknown')
                        slug = addon.get('slug', 'N/A')
                        version = addon.get('version', 'N/A')
                        description = addon.get('description', 'No description')
                        installed = addon.get('installed', False)
                        
                        result += f"#### {name}\n"
                        result += f"- **Slug**: `{slug}`\n"
                        result += f"- **Version**: {version}\n"
                        result += f"- **Status**: {'✓ Installed' if installed else 'Not installed'}\n"
                        result += f"- **Description**: {description}\n"
                        result += "\n"
                
                result += "## Usage\n\n"
                result += "To install an addon:\n"
                result += "```\ninstall_addon <addon_slug>\n```\n\n"
                result += "To check if an addon is compatible:\n"
                result += "```\ncheck_addon_availability <addon_slug>\n```\n"
                
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = "# Store Access Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = "# Store Access Failed\n\n"
                result += f"❌ **Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify network connectivity\n"
                result += "- Ensure Home Assistant can access the addon store\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "reload_addons":
            try:
                result = "# Reloading Add-on List\n\n"
                
                # Perform reload
                reload_result = await ha_client.reload_addons()
                
                result += "✓ **Add-on list reloaded successfully**\n\n"
                result += "The addon catalog has been refreshed. Any new addons from configured repositories should now be visible.\n\n"
                
                result += "## What This Does\n\n"
                result += "- Refreshes the list of available addons from all repositories\n"
                result += "- Updates addon metadata and versions\n"
                result += "- Does not affect running addons\n"
                result += "- No restart required\n\n"
                
                result += "## Next Steps\n\n"
                result += "- Use `list_store_addons` to see all available addons\n"
                result += "- Use `list_addons` to see installed addons\n"
                result += "- Install new addons with `install_addon <slug>`\n"
                
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = "# Reload Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = "# Reload Failed\n\n"
                result += f"❌ **Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify Supervisor is running properly\n"
                result += "- Try restarting Home Assistant if the issue persists\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "check_addon_availability":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            try:
                result = f"# Checking Availability: {addon_slug}\n\n"
                
                # Check availability
                availability = await ha_client.check_addon_availability(addon_slug)
                
                addon_name = availability.get('addon_name', addon_slug)
                available = availability.get('available', False)
                compatible = availability.get('compatible', False)
                architecture = availability.get('architecture', 'unknown')
                supported_archs = availability.get('supported_architectures', [])
                reason = availability.get('reason', '')
                
                result += f"## {addon_name}\n\n"
                result += f"**Addon Slug**: `{addon_slug}`\n\n"
                
                # Availability status
                if available:
                    result += "### ✅ Available for Installation\n\n"
                    result += "This addon can be installed on your system.\n\n"
                    
                    result += "**System Information:**\n"
                    result += f"- **Your Architecture**: {architecture}\n"
                    result += f"- **Supported Architectures**: {', '.join(supported_archs)}\n"
                    result += f"- **Compatible**: {'Yes' if compatible else 'No'}\n\n"
                    
                    result += "## Next Steps\n\n"
                    result += f"To install this addon:\n"
                    result += f"```\ninstall_addon {addon_slug}\n```\n"
                else:
                    result += "### ❌ Not Available for Installation\n\n"
                    
                    if reason:
                        result += f"**Reason**: {reason}\n\n"
                    
                    result += "**System Information:**\n"
                    result += f"- **Your Architecture**: {architecture}\n"
                    result += f"- **Supported Architectures**: {', '.join(supported_archs) if supported_archs else 'None specified'}\n"
                    result += f"- **Compatible**: {'Yes' if compatible else 'No'}\n\n"
                    
                    result += "## Troubleshooting\n\n"
                    if not compatible:
                        result += "**Architecture Incompatibility:**\n"
                        result += f"- This addon does not support your system architecture ({architecture})\n"
                        result += f"- Supported architectures: {', '.join(supported_archs) if supported_archs else 'None'}\n"
                        result += "- You cannot install this addon on your current system\n\n"
                    else:
                        result += "**Other Reasons:**\n"
                        result += "- The addon may have unmet dependencies\n"
                        result += "- The addon may require specific Home Assistant features\n"
                        result += "- Check the addon's documentation for requirements\n"
                        result += "- Verify your Home Assistant version is compatible\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                result = f"# Availability Check Failed\n\n"
                result += f"❌ **Error**: {str(ve)}\n\n"
                result += "**Possible reasons:**\n"
                result += "- Addon slug is incorrect or doesn't exist in the store\n"
                result += "- Addon is not available in any configured repository\n\n"
                result += "**Suggestions:**\n"
                result += "- Use `list_store_addons` to see available addons\n"
                result += "- Check the addon slug spelling\n"
                result += "- Verify repositories are properly configured\n"
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = f"# Availability Check Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = f"# Availability Check Failed\n\n"
                result += f"❌ **Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify network connectivity to addon store\n"
                result += "- Try reloading addons: `reload_addons`\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "get_supervisor_logs":
            try:
                result = "# Home Assistant Supervisor Logs\n\n"
                
                # Get supervisor logs
                logs = await ha_client.get_supervisor_logs()
                
                # Truncate logs if too long
                max_length = 15000
                if len(logs) > max_length:
                    # Get last N characters
                    logs = logs[-max_length:]
                    result += f"⚠️ **Note**: Logs truncated to last {max_length} characters for readability.\n\n"
                
                # Get last 100 lines for display
                log_lines = logs.strip().split('\n')
                recent_logs = log_lines[-100:] if len(log_lines) > 100 else log_lines
                
                result += f"## Recent Supervisor Activity ({len(recent_logs)} lines)\n\n"
                result += "```\n"
                result += "\n".join(recent_logs)
                result += "\n```\n\n"
                
                # Analyze logs for common patterns
                result += "## Log Analysis\n\n"
                
                # Check for errors
                error_lines = [line for line in recent_logs if any(pattern in line.lower() for pattern in ['error', 'failed', 'exception', 'fatal'])]
                if error_lines:
                    result += "### ⚠️ Errors Found\n\n"
                    result += f"Found {len(error_lines)} error-related entries in recent logs:\n\n"
                    result += "```\n"
                    result += "\n".join(error_lines[-10:])  # Last 10 errors
                    result += "\n```\n\n"
                else:
                    result += "### ✓ No Recent Errors\n\n"
                    result += "No obvious errors found in recent supervisor logs.\n\n"
                
                # Check for addon-related activity
                addon_lines = [line for line in recent_logs if any(pattern in line.lower() for pattern in ['addon', 'install', 'build', 'rebuild'])]
                if addon_lines:
                    result += "### 📦 Addon Activity\n\n"
                    result += f"Found {len(addon_lines)} addon-related entries:\n\n"
                    result += "```\n"
                    result += "\n".join(addon_lines[-15:])  # Last 15 addon activities
                    result += "\n```\n\n"
                
                # Check for warnings
                warning_lines = [line for line in recent_logs if 'warning' in line.lower() or 'warn' in line.lower()]
                if warning_lines:
                    result += "### ⚠️ Warnings\n\n"
                    result += f"Found {len(warning_lines)} warning entries:\n\n"
                    result += "```\n"
                    result += "\n".join(warning_lines[-10:])  # Last 10 warnings
                    result += "\n```\n\n"
                
                result += "## Usage Tips\n\n"
                result += "**When to check supervisor logs:**\n"
                result += "- After installing or building an addon\n"
                result += "- When an addon fails to start\n"
                result += "- During system updates or upgrades\n"
                result += "- When troubleshooting supervisor issues\n"
                result += "- To monitor system-level events\n\n"
                
                result += "**Common log patterns:**\n"
                result += "- `Building addon...` - Addon build in progress\n"
                result += "- `Addon ... installed` - Successful installation\n"
                result += "- `ERROR` - Something went wrong\n"
                result += "- `WARNING` - Potential issues to investigate\n"
                
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = "# Supervisor Logs Access Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = "# Supervisor Logs Access Failed\n\n"
                result += f"❌ **Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify Supervisor is running properly\n"
                result += "- Ensure the MCP server has proper permissions\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "restart_homeassistant":
            try:
                result = "# Restarting Home Assistant Core\n\n"
                
                result += "⚠️ **WARNING: This will restart Home Assistant Core**\n\n"
                result += "**What will happen:**\n"
                result += "- Home Assistant Core will restart\n"
                result += "- All clients will be temporarily disconnected\n"
                result += "- Integrations will reload\n"
                result += "- Automations will be reloaded\n"
                result += "- The Supervisor and addons will continue running\n\n"
                
                # Perform restart
                restart_result = await ha_client.restart_homeassistant()
                
                result += "✓ **Restart Initiated**\n\n"
                result += "Home Assistant Core is now restarting. This typically takes 30-60 seconds.\n\n"
                
                result += "## What to Expect\n\n"
                result += "1. **Connection Lost** - You will lose connection to Home Assistant temporarily\n"
                result += "2. **Services Reload** - All services and integrations will reload\n"
                result += "3. **Automations Resume** - Automations will resume after restart\n"
                result += "4. **Reconnection** - Clients will automatically reconnect when ready\n\n"
                
                result += "## Monitoring Restart\n\n"
                result += "- Wait 30-60 seconds for restart to complete\n"
                result += "- Check if Home Assistant UI is accessible\n"
                result += "- Verify integrations are working\n"
                result += "- Check logs if issues occur: `get_supervisor_logs`\n\n"
                
                result += "## When to Use This\n\n"
                result += "- After changing configuration.yaml\n"
                result += "- After installing/updating integrations\n"
                result += "- After modifying automations or scripts\n"
                result += "- When troubleshooting integration issues\n"
                result += "- After updating Home Assistant Core\n"
                
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = "# Restart Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = "# Restart Failed\n\n"
                result += f"❌ **Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify Supervisor is running properly\n"
                result += "- Ensure Home Assistant Core is responsive\n"
                result += "- Try restarting from the Home Assistant UI if this fails\n"
                return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown addon tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing addon tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
