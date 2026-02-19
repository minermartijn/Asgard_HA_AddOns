"""
MCP protocol handlers (tools, resources, etc.)
"""

import logging
from typing import Any
from mcp.types import Resource, TextContent, Tool
import mcp.types as types

from tools.addon import get_addon_tool_definitions, handle_addon_tool
from tools.backup_tools import get_backup_tool_definitions, handle_backup_tool
from tools.integration_tools import get_integration_tool_definitions, handle_integration_tool
from tools.entity_tools import get_entity_tool_definitions, handle_entity_tool
from tools.dashboard_tools import get_dashboard_tool_definitions, handle_dashboard_tools
from tools.automation_tools import get_automation_tool_definitions, handle_automation_tools
from tools.diagnostic import get_diagnostic_tool_definitions, handle_diagnostic_tool

logger = logging.getLogger(__name__)


def create_list_tools_handler(ha_client, enabled_tools: list[str] = None):
    """Create handler for listing available tools.
    
    Args:
        ha_client: Home Assistant client instance
        enabled_tools: List of tool names to enable. If None, all tools are enabled.
    """
    async def handle_list_tools() -> list[Tool]:
        """List available tools."""
        tools = []
        
        # Collect all tool definitions
        all_tools_list = []
        all_tools_list.extend(get_addon_tool_definitions())
        all_tools_list.extend(get_backup_tool_definitions())
        all_tools_list.extend(get_integration_tool_definitions())
        all_tools_list.extend(get_entity_tool_definitions())
        all_tools_list.extend(get_dashboard_tool_definitions())
        all_tools_list.extend(get_automation_tool_definitions())
        all_tools_list.extend(get_diagnostic_tool_definitions())
        
        # Filter tools based on enabled_tools configuration
        if enabled_tools is not None:
            filtered_tools = [tool for tool in all_tools_list if tool.name in enabled_tools]
            tools.extend(filtered_tools)
            logger.info(f"Filtered {len(filtered_tools)} tools from {len(all_tools_list)} available tools")
        else:
            tools.extend(all_tools_list)
        
        logger.info(f"Listing {len(tools)} available tools")
        return tools
    
    return handle_list_tools


def create_call_tool_handler(ha_client):
    """Create handler for executing tools."""
    async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution."""
        logger.info(f"Tool called: {name} with arguments: {arguments}")
        
        if arguments is None:
            arguments = {}
        
        # Define tool categories
        addon_tools = [
            "list_addons", "get_addon_info", "start_addon", "stop_addon", "restart_addon", 
            "get_addon_logs", "update_addon", "install_addon", "uninstall_addon",
            "get_addon_configuration", "set_addon_configuration", "validate_addon_configuration",
            "rebuild_addon", "list_store_addons", "reload_addons", "check_addon_availability",
            "get_supervisor_logs", "get_homeassistant_logs", "restart_homeassistant",
            "read_config_file", "write_config_file", "check_config"
        ]
        
        backup_tools = [
            "create_backup", "list_backups", "get_backup_info", "restore_backup", "delete_backup"
        ]
        
        integration_tools = [
            "list_integrations", "reload_integration", "get_integration_info", "remove_integration"
        ]
        
        entity_tools = [
            "list_entities", "get_entity_state", "set_entity_state", 
            "call_service", "get_services", "get_entity_history"
        ]
        
        dashboard_tools = [
            "list_dashboards", "get_dashboard_config", "create_dashboard", "delete_dashboard"
        ]
        
        automation_tools = [
            "list_automations", "get_automation", "create_automation", "update_automation",
            "delete_automation", "enable_automation", "disable_automation", "trigger_automation"
        ]
        
        diagnostic_tools = [
            "get_system_health", "get_error_log_summary", "list_unavailable_entities",
            "get_recorder_stats", "check_network_connectivity", "list_custom_components",
            "get_startup_time_breakdown", "validate_all_automations", "list_deprecated_features",
            "get_integration_diagnostics"
        ]
        
        # Route to appropriate tool handler
        if name in addon_tools:
            return await handle_addon_tool(name, arguments, ha_client)
        elif name in backup_tools:
            return await handle_backup_tool(name, arguments, ha_client)
        elif name in integration_tools:
            return await handle_integration_tool(name, arguments, ha_client)
        elif name in entity_tools:
            return await handle_entity_tool(name, arguments, ha_client)
        elif name in dashboard_tools:
            return await handle_dashboard_tools(name, arguments, ha_client)
        elif name in automation_tools:
            return await handle_automation_tools(name, arguments, ha_client)
        elif name in diagnostic_tools:
            return await handle_diagnostic_tool(name, arguments, ha_client)
        
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    return handle_call_tool


def create_list_resources_handler():
    """Create handler for listing available resources."""
    async def handle_list_resources() -> list[Resource]:
        """List available resources."""
        return [
            Resource(
                uri="ha://status",
                name="Home Assistant Status",
                description="Current Home Assistant instance status",
                mimeType="application/json",
            ),
            Resource(
                uri="ha://config",
                name="Home Assistant Configuration",
                description="Home Assistant configuration information",
                mimeType="application/json",
            ),
        ]
    
    return handle_list_resources


def create_read_resource_handler():
    """Create handler for reading resource content."""
    async def handle_read_resource(uri: str) -> str:
        """Read resource content."""
        logger.info(f"Reading resource: {uri}")
        
        if uri == "ha://status":
            return "Home Assistant is running"
        elif uri == "ha://config":
            return "Home Assistant configuration"
        
        raise ValueError(f"Unknown resource: {uri}")
    
    return handle_read_resource
