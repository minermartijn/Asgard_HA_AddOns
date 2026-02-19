"""
Store and addon management tool handlers.
Extracted from management_handlers.py for better maintainability.
"""
import asyncio
import logging
from typing import Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)


async def handle_store_addon_tools(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle store addon tool execution."""
    try:
        if name == "rebuild_addon":
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
        
        else:
            return [TextContent(type="text", text=f"Unknown store tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing store tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
