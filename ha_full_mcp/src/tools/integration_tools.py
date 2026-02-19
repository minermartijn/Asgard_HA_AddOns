"""Integration management tools for Home Assistant MCP Server."""
import logging
from typing import Any
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)


def get_integration_tool_definitions() -> list[Tool]:
    """Return all integration-related tool definitions."""
    return [
        Tool(
            name="list_integrations",
            description="List all configured integrations in Home Assistant with their status, domain, and entry details. Shows which integrations are loaded and working.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="reload_integration",
            description="Reload a specific integration without restarting Home Assistant. Useful for applying configuration changes or fixing integration issues. The integration will reconnect and reinitialize.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "The config entry ID of the integration to reload",
                    },
                },
                "required": ["entry_id"],
            },
        ),
        Tool(
            name="get_integration_info",
            description="Get detailed information about a specific integration including its configuration, entities, devices, and current status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "The config entry ID of the integration",
                    },
                },
                "required": ["entry_id"],
            },
        ),
        Tool(
            name="remove_integration",
            description="Remove/delete an integration from Home Assistant. WARNING: This will remove all entities and devices associated with this integration. The integration can be re-added later if needed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "The config entry ID of the integration to remove",
                    },
                },
                "required": ["entry_id"],
            },
        ),
    ]


async def handle_integration_tool(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle integration tool execution."""
    try:
        if name == "list_integrations":
            result = "# Home Assistant Integrations\n\n"
            
            integrations = await ha_client.list_integrations()
            
            if not integrations:
                result += "No integrations configured.\n\n"
                result += "Integrations are added through Settings → Devices & Services in the Home Assistant UI.\n"
                return [TextContent(type="text", text=result)]
            
            result += f"Found {len(integrations)} integration(s)\n\n"
            
            # Group by domain
            by_domain = {}
            for integration in integrations:
                domain = integration.get('domain', 'unknown')
                if domain not in by_domain:
                    by_domain[domain] = []
                by_domain[domain].append(integration)
            
            # Display grouped integrations
            for domain in sorted(by_domain.keys()):
                entries = by_domain[domain]
                result += f"## {domain.replace('_', ' ').title()} ({len(entries)})\n\n"
                
                for entry in entries:
                    title = entry.get('title', 'Unnamed')
                    entry_id = entry.get('entry_id', 'unknown')
                    state = entry.get('state', 'unknown')
                    
                    # Status indicator
                    status_icon = "✅" if state == "loaded" else "⚠️"
                    
                    result += f"{status_icon} **{title}**\n"
                    result += f"   - Entry ID: `{entry_id}`\n"
                    result += f"   - State: {state}\n"
                    
                    if entry.get('source'):
                        result += f"   - Source: {entry['source']}\n"
                    
                    result += "\n"
            
            result += "## 💡 Quick Actions\n\n"
            result += "- Get details: `get_integration_info <entry_id>`\n"
            result += "- Reload: `reload_integration <entry_id>`\n"
            result += "- Remove: `remove_integration <entry_id>`\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "reload_integration":
            entry_id = arguments.get("entry_id")
            if not entry_id:
                return [TextContent(type="text", text="Error: entry_id is required")]
            
            result = f"# Reloading Integration\n\n"
            result += f"**Entry ID**: `{entry_id}`\n\n"
            
            # Get integration info first
            try:
                info = await ha_client.get_integration_info(entry_id)
                result += f"**Integration**: {info.get('title', 'Unknown')}\n"
                result += f"**Domain**: {info.get('domain', 'Unknown')}\n\n"
            except Exception:
                result += "⚠️ Could not retrieve integration details\n\n"
            
            result += "⏳ **Reloading integration...**\n\n"
            result += "This will:\n"
            result += "- Disconnect the integration\n"
            result += "- Reload configuration\n"
            result += "- Reconnect and reinitialize\n"
            result += "- Update all entities\n\n"
            
            # Reload the integration
            reload_result = await ha_client.reload_integration(entry_id)
            
            result += "## ✅ Integration Reloaded\n\n"
            result += f"- **Status**: {reload_result.get('result', 'ok')}\n"
            result += f"- **Entry ID**: {entry_id}\n\n"
            
            result += "## 💡 Next Steps\n\n"
            result += "- Check that entities are updating correctly\n"
            result += "- Verify devices are responding\n"
            result += "- Check logs if any issues occur\n"
            result += f"- Get updated info: `get_integration_info {entry_id}`\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_integration_info":
            entry_id = arguments.get("entry_id")
            if not entry_id:
                return [TextContent(type="text", text="Error: entry_id is required")]
            
            result = f"# Integration Information\n\n"
            
            info = await ha_client.get_integration_info(entry_id)
            
            result += f"## {info.get('title', 'Unnamed Integration')}\n\n"
            
            # Basic info
            result += "### Basic Information\n\n"
            result += f"- **Entry ID**: `{info.get('entry_id')}`\n"
            result += f"- **Domain**: {info.get('domain', 'Unknown')}\n"
            result += f"- **State**: {info.get('state', 'Unknown')}\n"
            result += f"- **Source**: {info.get('source', 'Unknown')}\n"
            
            if info.get('version'):
                result += f"- **Version**: {info['version']}\n"
            
            result += "\n"
            
            # Configuration (if available and not sensitive)
            if info.get('data'):
                result += "### Configuration\n\n"
                result += "Configuration data is present (may contain sensitive information)\n\n"
            
            # Options (if available)
            if info.get('options'):
                result += "### Options\n\n"
                options = info['options']
                if isinstance(options, dict):
                    for key, value in options.items():
                        # Don't show sensitive values
                        if any(sensitive in key.lower() for sensitive in ['password', 'token', 'key', 'secret']):
                            result += f"- **{key}**: `[REDACTED]`\n"
                        else:
                            result += f"- **{key}**: `{value}`\n"
                result += "\n"
            
            # Entities count (if available)
            if info.get('entity_count'):
                result += f"### Entities\n\n"
                result += f"This integration provides **{info['entity_count']}** entities\n\n"
            
            # Devices count (if available)
            if info.get('device_count'):
                result += f"### Devices\n\n"
                result += f"This integration manages **{info['device_count']}** devices\n\n"
            
            result += "## 💡 Actions\n\n"
            result += f"- Reload: `reload_integration {entry_id}`\n"
            result += f"- Remove: `remove_integration {entry_id}`\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "remove_integration":
            entry_id = arguments.get("entry_id")
            if not entry_id:
                return [TextContent(type="text", text="Error: entry_id is required")]
            
            result = f"# Removing Integration\n\n"
            
            # Get integration info first
            try:
                info = await ha_client.get_integration_info(entry_id)
                result += f"## {info.get('title', 'Unnamed Integration')}\n\n"
                result += f"- **Domain**: {info.get('domain', 'Unknown')}\n"
                result += f"- **Entry ID**: `{entry_id}`\n\n"
            except Exception:
                result += f"**Entry ID**: `{entry_id}`\n\n"
            
            result += "⚠️ **WARNING: INTEGRATION REMOVAL**\n\n"
            result += "This will:\n"
            result += "- Remove the integration from Home Assistant\n"
            result += "- Delete all associated entities\n"
            result += "- Remove all associated devices\n"
            result += "- Clear integration configuration\n\n"
            result += "The integration can be re-added later through Settings → Devices & Services.\n\n"
            
            # Remove the integration
            remove_result = await ha_client.remove_integration(entry_id)
            
            result += "## ✅ Integration Removed\n\n"
            result += f"- **Status**: {remove_result.get('result', 'ok')}\n"
            result += f"- **Entry ID**: {entry_id}\n\n"
            
            result += "## 💡 What's Next\n\n"
            result += "- The integration has been removed from your system\n"
            result += "- All entities and devices are deleted\n"
            result += "- You can re-add it anytime from Settings → Devices & Services\n"
            result += "- Check `list_integrations` to see remaining integrations\n"
            
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown integration tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing integration tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
