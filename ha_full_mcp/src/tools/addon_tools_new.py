"""
Addon management tools for Home Assistant MCP Server.

This is a compatibility wrapper that imports from the refactored addon module.
The actual implementation is split across multiple files in src/tools/addon/
for better maintainability (each file under 500 lines).
"""
import asyncio
import logging
from typing import Any
from mcp.types import Tool, TextContent

# Import from refactored modules
from tools.addon.definitions import get_addon_tool_definitions
from tools.addon.basic_handlers import handle_basic_addon_tools
from tools.addon.lifecycle_handlers import handle_lifecycle_addon_tools
from tools.addon.config_handlers import handle_config_addon_tools
from tools.addon.management_handlers import handle_management_addon_tools
from tools.addon.system_handlers import handle_system_addon_tools

logger = logging.getLogger(__name__)


async def handle_addon_tool(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """
    Handle addon tool execution by routing to appropriate handler module.
    
    This function routes tool calls to specialized handler modules based on tool category.
    """
    # Basic tools: list, info
    basic_tools = ["list_addons", "get_addon_info"]
    if name in basic_tools:
        return await handle_basic_addon_tools(name, arguments, ha_client)
    
    # Lifecycle tools: start, stop, restart, logs, update
    lifecycle_tools = ["start_addon", "stop_addon", "restart_addon", "get_addon_logs", "update_addon"]
    if name in lifecycle_tools:
        return await handle_lifecycle_addon_tools(name, arguments, ha_client)
    
    # Configuration tools: get/set/validate config
    config_tools = ["get_addon_configuration", "set_addon_configuration", "validate_addon_configuration"]
    if name in config_tools:
        return await handle_config_addon_tools(name, arguments, ha_client)
    
    # Management tools: install, uninstall, rebuild, store, reload, availability
    management_tools = ["install_addon", "uninstall_addon", "rebuild_addon", 
                       "list_store_addons", "reload_addons", "check_addon_availability"]
    if name in management_tools:
        return await handle_management_addon_tools(name, arguments, ha_client)
    
    # System tools: supervisor/HA logs, restart, config files
    system_tools = ["get_supervisor_logs", "get_homeassistant_logs", "restart_homeassistant",
                   "read_config_file", "write_config_file", "check_config"]
    if name in system_tools:
        return await handle_system_addon_tools(name, arguments, ha_client)
    
    # Unknown tool
    return [TextContent(type="text", text=f"Unknown addon tool: {name}")]


__all__ = ['get_addon_tool_definitions', 'handle_addon_tool']
