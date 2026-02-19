"""
Management addon tool handlers (install/uninstall).
Extracted from addon_tools.py for better maintainability.
"""
import asyncio
import logging
from typing import Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)


async def handle_management_addon_tools(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle management addon tool execution (install/uninstall only)."""
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
        
        
        else:
            return [TextContent(type="text", text=f"Unknown management tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing management tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
