"""
Dashboard management tools for Home Assistant MCP Server.
"""
import logging
import json
from typing import Any
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)


def get_dashboard_tool_definitions() -> list[Tool]:
    """Return all dashboard-related tool definitions."""
    return [
        Tool(
            name="list_dashboards",
            description="List all Lovelace dashboards in Home Assistant. Shows available dashboards and their configurations.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_dashboard_config",
            description="Get the configuration of a specific dashboard. Use 'lovelace' for the default dashboard or provide a custom dashboard ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dashboard_id": {
                        "type": "string",
                        "description": "Dashboard ID (e.g., 'lovelace' for default, or custom ID). Leave empty for default dashboard.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="create_dashboard",
            description="Create a new Lovelace dashboard. Provide dashboard ID, title, and optionally views with cards. The dashboard will appear in the Home Assistant sidebar.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dashboard_id": {
                        "type": "string",
                        "description": "Unique dashboard ID (URL path, e.g., 'bachlaan31'). Cannot be 'lovelace' (reserved for default).",
                    },
                    "title": {
                        "type": "string",
                        "description": "Dashboard title shown in sidebar",
                    },
                    "icon": {
                        "type": "string",
                        "description": "Dashboard icon (default: mdi:view-dashboard). Use Material Design Icons format.",
                    },
                    "show_in_sidebar": {
                        "type": "boolean",
                        "description": "Show dashboard in sidebar (default: true)",
                    },
                    "views": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Optional: Array of view configurations. Each view contains title, icon, and cards. Can be added later.",
                    },
                },
                "required": ["dashboard_id", "title"],
            },
        ),
        Tool(
            name="delete_dashboard",
            description="Delete a custom dashboard. Cannot delete the default 'lovelace' dashboard.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dashboard_id": {
                        "type": "string",
                        "description": "Dashboard ID to delete (cannot be 'lovelace')",
                    },
                },
                "required": ["dashboard_id"],
            },
        ),
    ]


async def handle_dashboard_tools(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle dashboard tool execution."""
    try:
        if name == "list_dashboards":
            result = "# Home Assistant Dashboards\n\n"
            
            try:
                # Get dashboard resources
                data = await ha_client.list_dashboards()
                
                result += "## Available Dashboards\n\n"
                result += "- **Default Dashboard** (lovelace)\n"
                result += "- Access via Home Assistant UI\n\n"
                
                result += "## 💡 Quick Actions\n\n"
                result += "- View config: `get_dashboard_config <dashboard_id>`\n"
                result += "- Create new: `create_dashboard <dashboard_id> <config>`\n"
                result += "- Delete: `delete_dashboard <dashboard_id>`\n"
                
            except Exception as e:
                result += f"⚠️ Could not list dashboards: {e}\n\n"
                result += "Note: Dashboard listing may require additional permissions.\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_dashboard_config":
            dashboard_id = arguments.get("dashboard_id")
            
            result = f"# Dashboard Configuration\n\n"
            result += f"**Dashboard**: {dashboard_id or 'default (lovelace)'}\n\n"
            
            try:
                config = await ha_client.get_dashboard_config(dashboard_id)
                
                result += "## Configuration\n\n"
                result += "```json\n"
                result += json.dumps(config, indent=2)
                result += "\n```\n\n"
                
                # Show summary
                if "views" in config:
                    result += f"**Views**: {len(config['views'])}\n"
                    for i, view in enumerate(config['views'], 1):
                        view_title = view.get('title', f'View {i}')
                        cards_count = len(view.get('cards', []))
                        result += f"- {view_title}: {cards_count} cards\n"
                
            except Exception as e:
                result += f"❌ Error: {e}\n\n"
                result += "This dashboard may not exist or you may not have permission to access it.\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "create_dashboard":
            dashboard_id = arguments.get("dashboard_id")
            title = arguments.get("title")
            views = arguments.get("views")
            icon = arguments.get("icon", "mdi:view-dashboard")
            show_in_sidebar = arguments.get("show_in_sidebar", True)
            
            if not dashboard_id or not title:
                return [TextContent(type="text", text="Error: dashboard_id and title are required")]
            
            result = f"# Creating Dashboard: {title}\n\n"
            result += f"**Dashboard ID**: {dashboard_id}\n\n"
            
            try:
                # Step 1: Create the dashboard entry
                dashboard_info = await ha_client.create_dashboard(
                    dashboard_id=dashboard_id,
                    title=title,
                    icon=icon,
                    show_in_sidebar=show_in_sidebar
                )
                
                result += "## ✅ Dashboard Created Successfully\n\n"
                result += f"**Title**: {title}\n"
                result += f"**Icon**: {icon}\n"
                result += f"**Sidebar**: {'Yes' if show_in_sidebar else 'No'}\n\n"
                
                # Step 2: If views provided, update the configuration
                if views:
                    config = {"views": views}
                    await ha_client.update_dashboard_config(dashboard_id, config)
                    
                    result += f"**Views**: {len(views)}\n"
                    for i, view in enumerate(views, 1):
                        view_title = view.get('title', f'View {i}')
                        cards_count = len(view.get('cards', []))
                        result += f"- {view_title}: {cards_count} cards\n"
                    result += "\n"
                
                result += "## 💡 Next Steps\n\n"
                result += f"1. Open Home Assistant UI\n"
                result += f"2. Look for '{title}' in the sidebar\n"
                result += f"3. View config: `get_dashboard_config {dashboard_id}`\n"
                result += f"4. Update views: Use `update_dashboard_config` if needed\n"
                
            except Exception as e:
                result += f"## ❌ Error Creating Dashboard\n\n"
                result += f"**Error**: {e}\n\n"
                result += "**Possible causes:**\n"
                result += "- Dashboard ID already exists\n"
                result += "- Invalid dashboard configuration\n"
                result += "- Insufficient permissions\n"
                result += "- WebSocket connection issue\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "delete_dashboard":
            dashboard_id = arguments.get("dashboard_id")
            
            if not dashboard_id:
                return [TextContent(type="text", text="Error: dashboard_id is required")]
            
            if dashboard_id == "lovelace":
                return [TextContent(type="text", text="Error: Cannot delete the default 'lovelace' dashboard")]
            
            result = f"# Deleting Dashboard: {dashboard_id}\n\n"
            
            try:
                await ha_client.delete_dashboard(dashboard_id)
                
                result += "## ✅ Dashboard Deleted Successfully\n\n"
                result += f"**Dashboard ID**: {dashboard_id}\n\n"
                result += "The dashboard has been removed from Home Assistant.\n"
                
            except Exception as e:
                result += f"## ❌ Error Deleting Dashboard\n\n"
                result += f"**Error**: {e}\n\n"
                result += "**Possible causes:**\n"
                result += "- Dashboard does not exist\n"
                result += "- Insufficient permissions\n"
            
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown dashboard tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing dashboard tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
