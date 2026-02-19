"""
Lifecycle addon tool handlers.
Extracted from addon_tools.py for better maintainability.
"""
import asyncio
import logging
from typing import Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)


async def handle_lifecycle_addon_tools(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle lifecycle addon tool execution."""
    try:
        if name == "start_addon":
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
        
        else:
            return [TextContent(type="text", text=f"Unknown lifecycle tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing lifecycle tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
