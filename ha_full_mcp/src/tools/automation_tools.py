"""
Automation management tools for Home Assistant MCP Server.
"""
import logging
import json
from typing import Any
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)


def get_automation_tool_definitions() -> list[Tool]:
    """Return all automation-related tool definitions."""
    return [
        Tool(
            name="list_automations",
            description="List all Home Assistant automations with their status, triggers, and actions. Shows enabled/disabled state.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_automation",
            description="Get detailed information about a specific automation including triggers, conditions, and actions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "automation_id": {
                        "type": "string",
                        "description": "Automation ID (from list_automations)",
                    },
                },
                "required": ["automation_id"],
            },
        ),
        Tool(
            name="create_automation",
            description="Create a new automation with triggers, conditions, and actions. Automations run automatically when triggered.",
            inputSchema={
                "type": "object",
                "properties": {
                    "alias": {
                        "type": "string",
                        "description": "Automation name/alias",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of what the automation does",
                    },
                    "trigger": {
                        "type": "array",
                        "description": "List of triggers (e.g., state change, time, event)",
                    },
                    "condition": {
                        "type": "array",
                        "description": "Optional list of conditions that must be met",
                    },
                    "action": {
                        "type": "array",
                        "description": "List of actions to perform when triggered",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Execution mode: single, restart, queued, parallel (default: single)",
                    },
                },
                "required": ["alias", "trigger", "action"],
            },
        ),
        Tool(
            name="update_automation",
            description="Update an existing automation's configuration. Modifies triggers, conditions, or actions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "automation_id": {
                        "type": "string",
                        "description": "Automation ID to update",
                    },
                    "alias": {
                        "type": "string",
                        "description": "Automation name/alias",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description",
                    },
                    "trigger": {
                        "type": "array",
                        "description": "List of triggers",
                    },
                    "condition": {
                        "type": "array",
                        "description": "Optional list of conditions",
                    },
                    "action": {
                        "type": "array",
                        "description": "List of actions",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Execution mode",
                    },
                },
                "required": ["automation_id"],
            },
        ),
        Tool(
            name="delete_automation",
            description="Delete an automation permanently. This cannot be undone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "automation_id": {
                        "type": "string",
                        "description": "Automation ID to delete",
                    },
                },
                "required": ["automation_id"],
            },
        ),
        Tool(
            name="enable_automation",
            description="Enable a disabled automation. The automation will start responding to triggers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Automation entity ID (e.g., automation.my_automation)",
                    },
                },
                "required": ["entity_id"],
            },
        ),
        Tool(
            name="disable_automation",
            description="Disable an automation. It will stop responding to triggers but remain configured.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Automation entity ID (e.g., automation.my_automation)",
                    },
                },
                "required": ["entity_id"],
            },
        ),
        Tool(
            name="trigger_automation",
            description="Manually trigger an automation, optionally skipping conditions. Useful for testing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Automation entity ID (e.g., automation.my_automation)",
                    },
                    "skip_condition": {
                        "type": "boolean",
                        "description": "Skip condition checks (default: true)",
                    },
                },
                "required": ["entity_id"],
            },
        ),
    ]


async def handle_automation_tools(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle automation tool execution."""
    try:
        if name == "list_automations":
            result = "# Home Assistant Automations\n\n"
            
            try:
                automations = await ha_client.list_automations()
                
                if not automations:
                    result += "No automations found.\n"
                else:
                    result += f"Found {len(automations)} automation(s)\n\n"
                    
                    for auto in automations:
                        auto_id = auto.get('id', 'unknown')
                        alias = auto.get('alias', 'Unnamed')
                        description = auto.get('description', '')
                        
                        result += f"## {alias}\n\n"
                        result += f"- **ID**: `{auto_id}`\n"
                        if description:
                            result += f"- **Description**: {description}\n"
                        
                        # Show triggers
                        triggers = auto.get('trigger', [])
                        if triggers:
                            result += f"- **Triggers**: {len(triggers)} trigger(s)\n"
                        
                        # Show actions
                        actions = auto.get('action', [])
                        if actions:
                            result += f"- **Actions**: {len(actions)} action(s)\n"
                        
                        result += "\n"
                
                result += "## 💡 Quick Actions\n\n"
                result += "- View details: `get_automation <automation_id>`\n"
                result += "- Create new: `create_automation`\n"
                result += "- Enable: `enable_automation <entity_id>`\n"
                result += "- Disable: `disable_automation <entity_id>`\n"
                
            except Exception as e:
                result += f"❌ Error: {e}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_automation":
            automation_id = arguments.get("automation_id")
            
            if not automation_id:
                return [TextContent(type="text", text="Error: automation_id is required")]
            
            result = f"# Automation Details\n\n"
            result += f"**ID**: {automation_id}\n\n"
            
            try:
                automation = await ha_client.get_automation(automation_id)
                
                if not automation:
                    result += "❌ Automation not found\n"
                else:
                    result += f"**Alias**: {automation.get('alias', 'Unnamed')}\n"
                    
                    description = automation.get('description')
                    if description:
                        result += f"**Description**: {description}\n"
                    
                    result += "\n## Configuration\n\n"
                    result += "```json\n"
                    result += json.dumps(automation, indent=2)
                    result += "\n```\n"
                
            except Exception as e:
                result += f"❌ Error: {e}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "create_automation":
            alias = arguments.get("alias")
            trigger = arguments.get("trigger")
            action = arguments.get("action")
            
            if not alias or not trigger or not action:
                return [TextContent(type="text", text="Error: alias, trigger, and action are required")]
            
            result = f"# Creating Automation: {alias}\n\n"
            
            try:
                # Generate automation ID from alias
                import re
                automation_id = re.sub(r'[^a-z0-9_]', '_', alias.lower())
                
                config = {
                    "alias": alias,
                    "trigger": trigger,
                    "action": action,
                }
                
                # Optional fields
                if arguments.get("description"):
                    config["description"] = arguments["description"]
                if arguments.get("condition"):
                    config["condition"] = arguments["condition"]
                if arguments.get("mode"):
                    config["mode"] = arguments["mode"]
                
                response = await ha_client.create_automation(automation_id, config)
                
                result += "## ✅ Automation Created Successfully\n\n"
                result += f"**Alias**: {alias}\n"
                result += f"**ID**: {automation_id}\n"
                result += f"**Triggers**: {len(trigger)}\n"
                result += f"**Actions**: {len(action)}\n\n"
                
                result += "## 💡 Next Steps\n\n"
                result += "1. The automation is now active\n"
                result += f"2. Test it: `trigger_automation automation.{automation_id}`\n"
                result += "3. View all: `list_automations`\n"
                
            except Exception as e:
                result += f"## ❌ Error Creating Automation\n\n"
                result += f"**Error**: {e}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "update_automation":
            automation_id = arguments.get("automation_id")
            
            if not automation_id:
                return [TextContent(type="text", text="Error: automation_id is required")]
            
            result = f"# Updating Automation\n\n"
            result += f"**ID**: {automation_id}\n\n"
            
            try:
                # Get current config
                current = await ha_client.get_automation(automation_id)
                if not current:
                    return [TextContent(type="text", text=f"Error: Automation {automation_id} not found")]
                
                # Merge with updates
                config = current.copy()
                for key in ["alias", "description", "trigger", "condition", "action", "mode"]:
                    if key in arguments and arguments[key] is not None:
                        config[key] = arguments[key]
                
                response = await ha_client.update_automation(automation_id, config)
                
                result += "## ✅ Automation Updated Successfully\n\n"
                result += f"**Alias**: {config.get('alias')}\n"
                result += "Changes applied and active.\n"
                
            except Exception as e:
                result += f"## ❌ Error Updating Automation\n\n"
                result += f"**Error**: {e}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "delete_automation":
            automation_id = arguments.get("automation_id")
            
            if not automation_id:
                return [TextContent(type="text", text="Error: automation_id is required")]
            
            result = f"# Deleting Automation\n\n"
            result += f"**ID**: {automation_id}\n\n"
            
            try:
                await ha_client.delete_automation(automation_id)
                
                result += "## ✅ Automation Deleted Successfully\n\n"
                result += "The automation has been permanently removed.\n"
                
            except Exception as e:
                result += f"## ❌ Error Deleting Automation\n\n"
                result += f"**Error**: {e}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "enable_automation":
            entity_id = arguments.get("entity_id")
            
            if not entity_id:
                return [TextContent(type="text", text="Error: entity_id is required")]
            
            result = f"# Enabling Automation\n\n"
            result += f"**Entity**: {entity_id}\n\n"
            
            try:
                await ha_client.enable_automation(entity_id)
                
                result += "## ✅ Automation Enabled\n\n"
                result += "The automation is now active and will respond to triggers.\n"
                
            except Exception as e:
                result += f"## ❌ Error Enabling Automation\n\n"
                result += f"**Error**: {e}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "disable_automation":
            entity_id = arguments.get("entity_id")
            
            if not entity_id:
                return [TextContent(type="text", text="Error: entity_id is required")]
            
            result = f"# Disabling Automation\n\n"
            result += f"**Entity**: {entity_id}\n\n"
            
            try:
                await ha_client.disable_automation(entity_id)
                
                result += "## ✅ Automation Disabled\n\n"
                result += "The automation will not respond to triggers until re-enabled.\n"
                
            except Exception as e:
                result += f"## ❌ Error Disabling Automation\n\n"
                result += f"**Error**: {e}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "trigger_automation":
            entity_id = arguments.get("entity_id")
            skip_condition = arguments.get("skip_condition", True)
            
            if not entity_id:
                return [TextContent(type="text", text="Error: entity_id is required")]
            
            result = f"# Triggering Automation\n\n"
            result += f"**Entity**: {entity_id}\n"
            result += f"**Skip Conditions**: {skip_condition}\n\n"
            
            try:
                await ha_client.trigger_automation(entity_id, skip_condition)
                
                result += "## ✅ Automation Triggered\n\n"
                result += "The automation has been manually executed.\n"
                
            except Exception as e:
                result += f"## ❌ Error Triggering Automation\n\n"
                result += f"**Error**: {e}\n"
            
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown automation tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing automation tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
