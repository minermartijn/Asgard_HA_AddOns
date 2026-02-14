"""
MCP protocol handlers (tools, resources, etc.)
"""

import logging
from typing import Any
from mcp.types import Resource, TextContent, Tool
import mcp.types as types

from tools.addon_tools import get_addon_tool_definitions, handle_addon_tool

logger = logging.getLogger(__name__)


def create_list_tools_handler(ha_client):
    """Create handler for listing available tools."""
    async def handle_list_tools() -> list[Tool]:
        """List available tools."""
        tools = []
        
        # Add addon management tools
        tools.extend(get_addon_tool_definitions())
        
        # Future: Add entity tools
        # tools.extend(get_entity_tool_definitions())
        
        # Future: Add automation tools
        # tools.extend(get_automation_tool_definitions())
        
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
        
        # Route to appropriate tool handler based on tool name
        addon_tools = [
            "list_addons", "get_addon_info", "start_addon", "stop_addon", "restart_addon", 
            "get_addon_logs", "update_addon", "install_addon", "uninstall_addon",
            "get_addon_configuration", "set_addon_configuration", "validate_addon_configuration",
            "rebuild_addon", "list_store_addons", "reload_addons", "check_addon_availability",
            "get_supervisor_logs", "restart_homeassistant"
        ]
        
        if name in addon_tools:
            return await handle_addon_tool(name, arguments, ha_client)
        
        # Future: Add other tool categories
        # if name in entity_tools:
        #     return await handle_entity_tool(name, arguments, ha_client)
        
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
