"""
Addon management tools - refactored for maintainability.

This module provides all addon-related MCP tools, split into focused
categories for better organization and AI-friendliness.
"""
from .definitions import get_addon_tool_definitions
from .basic_handlers import handle_basic_addon_tools
from .lifecycle_handlers import handle_lifecycle_addon_tools
from .addon_config_handlers import handle_config_addon_tools
from .management_handlers import handle_management_addon_tools
from .store_handlers import handle_store_addon_tools
from .logs_handlers import handle_logs_addon_tools
from .config_file_handlers import handle_config_file_addon_tools

from typing import Any
from mcp.types import TextContent


async def handle_addon_tool(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """
    Route addon tool calls to appropriate handler module.
    
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
    
    # Addon configuration tools: get/set/validate addon config
    config_tools = ["get_addon_configuration", "set_addon_configuration", "validate_addon_configuration"]
    if name in config_tools:
        return await handle_config_addon_tools(name, arguments, ha_client)
    
    # Management tools: install, uninstall
    management_tools = ["install_addon", "uninstall_addon"]
    if name in management_tools:
        return await handle_management_addon_tools(name, arguments, ha_client)
    
    # Store tools: rebuild, list_store, reload, availability
    store_tools = ["rebuild_addon", "list_store_addons", "reload_addons", "check_addon_availability"]
    if name in store_tools:
        return await handle_store_addon_tools(name, arguments, ha_client)
    
    # Logs tools: supervisor/HA logs, restart
    logs_tools = ["get_supervisor_logs", "get_homeassistant_logs", "restart_homeassistant"]
    if name in logs_tools:
        return await handle_logs_addon_tools(name, arguments, ha_client)
    
    # Config file tools: read/write/check config files
    config_file_tools = ["read_config_file", "write_config_file", "check_config"]
    if name in config_file_tools:
        return await handle_config_file_addon_tools(name, arguments, ha_client)
    
    # Unknown tool
    return [TextContent(type="text", text=f"Unknown addon tool: {name}")]


__all__ = [
    'get_addon_tool_definitions',
    'handle_addon_tool',
]
