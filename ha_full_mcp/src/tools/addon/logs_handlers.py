"""
Logs and system restart tool handlers.
Extracted from system_handlers.py for better maintainability.
"""
import logging
from typing import Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)


async def handle_logs_addon_tools(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle logs addon tool execution."""
    try:
        if name == "get_supervisor_logs":
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
        
        elif name == "get_homeassistant_logs":
            try:
                result = "# Home Assistant Core Logs\n\n"
                
                # Get Home Assistant Core logs
                logs = await ha_client.get_homeassistant_logs()
                
                # Truncate logs if too long
                max_length = 15000
                if len(logs) > max_length:
                    # Get last N characters
                    logs = logs[-max_length:]
                    result += f"⚠️ **Note**: Logs truncated to last {max_length} characters for readability.\n\n"
                
                # Get last 100 lines for display
                log_lines = logs.strip().split('\n')
                recent_logs = log_lines[-100:] if len(log_lines) > 100 else log_lines
                
                result += f"## Recent Core Activity ({len(recent_logs)} lines)\n\n"
                result += "```\n"
                result += "\n".join(recent_logs)
                result += "\n```\n\n"
                
                # Analyze logs for common patterns
                result += "## Log Analysis\n\n"
                
                # Check for errors
                error_lines = [line for line in recent_logs if any(pattern in line.lower() for pattern in ['error', 'failed', 'exception', 'fatal', 'critical'])]
                if error_lines:
                    result += "### ⚠️ Errors Found\n\n"
                    result += f"Found {len(error_lines)} error-related entries in recent logs:\n\n"
                    result += "```\n"
                    result += "\n".join(error_lines[-10:])  # Last 10 errors
                    result += "\n```\n\n"
                else:
                    result += "### ✓ No Recent Errors\n\n"
                    result += "No obvious errors found in recent Home Assistant logs.\n\n"
                
                # Check for component/integration activity
                component_lines = [line for line in recent_logs if any(pattern in line.lower() for pattern in ['setup', 'setting up', 'loaded', 'integration'])]
                if component_lines:
                    result += "### 🔌 Component/Integration Activity\n\n"
                    result += f"Found {len(component_lines)} component-related entries:\n\n"
                    result += "```\n"
                    result += "\n".join(component_lines[-15:])  # Last 15 component activities
                    result += "\n```\n\n"
                
                # Check for warnings
                warning_lines = [line for line in recent_logs if 'warning' in line.lower() or 'warn' in line.lower()]
                if warning_lines:
                    result += "### ⚠️ Warnings\n\n"
                    result += f"Found {len(warning_lines)} warning entries:\n\n"
                    result += "```\n"
                    result += "\n".join(warning_lines[-10:])  # Last 10 warnings
                    result += "\n```\n\n"
                
                # Check for automation/script activity
                automation_lines = [line for line in recent_logs if any(pattern in line.lower() for pattern in ['automation', 'script', 'trigger'])]
                if automation_lines:
                    result += "### 🤖 Automation/Script Activity\n\n"
                    result += f"Found {len(automation_lines)} automation-related entries:\n\n"
                    result += "```\n"
                    result += "\n".join(automation_lines[-10:])  # Last 10 automation activities
                    result += "\n```\n\n"
                
                result += "## Usage Tips\n\n"
                result += "**When to check Home Assistant logs:**\n"
                result += "- After changing configuration.yaml\n"
                result += "- When integrations fail to load\n"
                result += "- When automations aren't working\n"
                result += "- When entities show as unavailable\n"
                result += "- During troubleshooting of any HA Core issue\n"
                result += "- After Home Assistant restart\n\n"
                
                result += "**Common log patterns:**\n"
                result += "- `Setup of domain ... took X seconds` - Component loading\n"
                result += "- `ERROR` - Something went wrong\n"
                result += "- `WARNING` - Potential issues to investigate\n"
                result += "- `Initialized trigger` - Automation loaded\n"
                result += "- `Platform error` - Integration/platform issue\n"
                
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = "# Home Assistant Logs Access Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = "# Home Assistant Logs Access Failed\n\n"
                result += f"❌ **Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Supervisor logs for more details\n"
                result += "- Verify Home Assistant Core is running\n"
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
            return [TextContent(type="text", text=f"Unknown logs tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing logs tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
