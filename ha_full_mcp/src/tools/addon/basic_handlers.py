"""
Basic addon tool handlers.
Extracted from addon_tools.py for better maintainability.
"""
import asyncio
import logging
from typing import Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)


async def handle_basic_addon_tools(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle basic addon tool execution."""
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
        
        if name == "get_addon_info":
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
        
        else:
            return [TextContent(type="text", text=f"Unknown basic tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing basic tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
