"""Entity management tools for Home Assistant MCP Server."""
import logging
from typing import Any
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)


def get_entity_tool_definitions() -> list[Tool]:
    """Return all entity-related tool definitions."""
    return [
        Tool(
            name="list_entities",
            description="List all entities in Home Assistant with their current states. Can filter by domain (e.g., 'light', 'switch', 'sensor') or area. Shows entity IDs, friendly names, states, and attributes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Optional domain filter (e.g., 'light', 'switch', 'sensor', 'binary_sensor', 'climate')",
                    },
                    "area_id": {
                        "type": "string",
                        "description": "Optional area ID to filter entities by location",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_entity_state",
            description="Get the current state and all attributes of a specific entity. Shows detailed information including state, last changed/updated times, and all entity attributes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The entity ID to get state for (e.g., 'light.living_room', 'sensor.temperature')",
                    },
                },
                "required": ["entity_id"],
            },
        ),
        Tool(
            name="set_entity_state",
            description="Set the state of an entity directly. This updates the entity's state in Home Assistant. Note: For controlling devices, use call_service instead. This is mainly for updating sensor values or manual state management.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The entity ID to set state for (e.g., 'sensor.custom_sensor')",
                    },
                    "state": {
                        "type": "string",
                        "description": "The new state value (e.g., 'on', 'off', '23.5')",
                    },
                    "attributes": {
                        "type": "object",
                        "description": "Optional attributes to set along with the state",
                    },
                },
                "required": ["entity_id", "state"],
            },
        ),
        Tool(
            name="call_service",
            description="Call a Home Assistant service to control devices or trigger actions. Services are the primary way to control entities (turn on/off lights, set climate temperature, etc.). Use get_services to see available services.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Service domain (e.g., 'light', 'switch', 'climate', 'automation')",
                    },
                    "service": {
                        "type": "string",
                        "description": "Service name (e.g., 'turn_on', 'turn_off', 'toggle', 'set_temperature')",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Optional entity ID to target (e.g., 'light.living_room'). Can also be a list.",
                    },
                    "data": {
                        "type": "object",
                        "description": "Optional service data/parameters (e.g., {'brightness': 255, 'color_name': 'red'})",
                    },
                },
                "required": ["domain", "service"],
            },
        ),
        Tool(
            name="get_services",
            description="List all available services in Home Assistant grouped by domain. Shows service names, descriptions, and required/optional parameters. Essential for discovering what actions you can perform.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_entity_history",
            description="Get historical state changes for an entity over a time period. Useful for analyzing trends, debugging automations, or reviewing past states. Returns timestamped state changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The entity ID to get history for (e.g., 'sensor.temperature')",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Optional start time in ISO format (e.g., '2024-01-01T00:00:00'). Defaults to 24 hours ago.",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Optional end time in ISO format. Defaults to now.",
                    },
                },
                "required": ["entity_id"],
            },
        ),
    ]


async def handle_entity_tool(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle entity tool execution."""
    try:
        if name == "list_entities":
            domain = arguments.get("domain")
            area_id = arguments.get("area_id")
            
            result = "# Home Assistant Entities\n\n"
            
            entities = await ha_client.list_entities(domain=domain, area_id=area_id)
            
            if not entities:
                result += "No entities found"
                if domain:
                    result += f" in domain '{domain}'"
                if area_id:
                    result += f" in area '{area_id}'"
                result += ".\n"
                return [TextContent(type="text", text=result)]
            
            # Add filter info
            if domain or area_id:
                result += "## Filters Applied\n\n"
                if domain:
                    result += f"- **Domain**: {domain}\n"
                if area_id:
                    result += f"- **Area**: {area_id}\n"
                result += "\n"
            
            result += f"Found {len(entities)} entit{'y' if len(entities) == 1 else 'ies'}\n\n"
            
            # Group by domain
            by_domain = {}
            for entity in entities:
                entity_domain = entity.get('entity_id', '').split('.')[0] if '.' in entity.get('entity_id', '') else 'unknown'
                if entity_domain not in by_domain:
                    by_domain[entity_domain] = []
                by_domain[entity_domain].append(entity)
            
            # Display grouped entities
            for entity_domain in sorted(by_domain.keys()):
                domain_entities = by_domain[entity_domain]
                result += f"## {entity_domain.replace('_', ' ').title()} ({len(domain_entities)})\n\n"
                
                for entity in domain_entities[:20]:  # Limit to 20 per domain
                    entity_id = entity.get('entity_id', 'unknown')
                    state = entity.get('state', 'unknown')
                    name = entity.get('attributes', {}).get('friendly_name', entity_id)
                    
                    result += f"- **{name}** (`{entity_id}`)\n"
                    result += f"  - State: {state}\n"
                
                if len(domain_entities) > 20:
                    result += f"  - ... and {len(domain_entities) - 20} more\n"
                
                result += "\n"
            
            result += "## 💡 Quick Actions\n\n"
            result += "- Get details: `get_entity_state <entity_id>`\n"
            result += "- Control device: `call_service <domain> <service> <entity_id>`\n"
            result += "- View history: `get_entity_history <entity_id>`\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_entity_state":
            entity_id = arguments.get("entity_id")
            if not entity_id:
                return [TextContent(type="text", text="Error: entity_id is required")]
            
            result = f"# Entity State: {entity_id}\n\n"
            
            state_data = await ha_client.get_entity_state(entity_id)
            
            # Basic info
            result += "## Current State\n\n"
            result += f"- **Entity ID**: `{state_data.get('entity_id')}`\n"
            result += f"- **State**: {state_data.get('state')}\n"
            result += f"- **Last Changed**: {state_data.get('last_changed')}\n"
            result += f"- **Last Updated**: {state_data.get('last_updated')}\n\n"
            
            # Attributes
            attributes = state_data.get('attributes', {})
            if attributes:
                result += "## Attributes\n\n"
                
                # Show friendly name first if available
                if 'friendly_name' in attributes:
                    result += f"- **Friendly Name**: {attributes['friendly_name']}\n"
                
                # Show other important attributes
                important_attrs = ['unit_of_measurement', 'device_class', 'state_class', 'icon']
                for attr in important_attrs:
                    if attr in attributes:
                        result += f"- **{attr.replace('_', ' ').title()}**: {attributes[attr]}\n"
                
                # Show remaining attributes
                other_attrs = {k: v for k, v in attributes.items() 
                              if k not in ['friendly_name'] + important_attrs}
                
                if other_attrs:
                    result += "\n### Additional Attributes\n\n"
                    for key, value in sorted(other_attrs.items()):
                        # Truncate long values
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                        result += f"- **{key}**: {value_str}\n"
            
            result += "\n## 💡 Actions\n\n"
            result += f"- View history: `get_entity_history {entity_id}`\n"
            
            # Suggest relevant services based on domain
            domain = entity_id.split('.')[0] if '.' in entity_id else ''
            if domain in ['light', 'switch', 'fan']:
                result += f"- Turn on: `call_service {domain} turn_on {entity_id}`\n"
                result += f"- Turn off: `call_service {domain} turn_off {entity_id}`\n"
            elif domain == 'climate':
                result += f"- Set temperature: `call_service climate set_temperature {entity_id}`\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "set_entity_state":
            entity_id = arguments.get("entity_id")
            state = arguments.get("state")
            attributes = arguments.get("attributes", {})
            
            if not entity_id or state is None:
                return [TextContent(type="text", text="Error: entity_id and state are required")]
            
            result = f"# Setting Entity State\n\n"
            result += f"**Entity**: `{entity_id}`\n"
            result += f"**New State**: {state}\n\n"
            
            if attributes:
                result += "**Attributes**:\n"
                for key, value in attributes.items():
                    result += f"- {key}: {value}\n"
                result += "\n"
            
            # Set the state
            set_result = await ha_client.set_entity_state(entity_id, state, attributes)
            
            result += "## ✅ State Updated\n\n"
            result += f"- **Entity**: {entity_id}\n"
            result += f"- **State**: {set_result.get('state')}\n"
            result += f"- **Last Changed**: {set_result.get('last_changed')}\n\n"
            
            result += "## 💡 Note\n\n"
            result += "State has been updated in Home Assistant. For controlling devices, "
            result += "consider using `call_service` instead for proper device control.\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "call_service":
            domain = arguments.get("domain")
            service = arguments.get("service")
            entity_id = arguments.get("entity_id")
            data = arguments.get("data", {})
            
            if not domain or not service:
                return [TextContent(type="text", text="Error: domain and service are required")]
            
            result = f"# Calling Service\n\n"
            result += f"**Service**: `{domain}.{service}`\n"
            
            if entity_id:
                result += f"**Target**: `{entity_id}`\n"
            
            if data:
                result += "\n**Parameters**:\n"
                for key, value in data.items():
                    result += f"- {key}: {value}\n"
            
            result += "\n⏳ **Executing service call...**\n\n"
            
            # Call the service
            service_result = await ha_client.call_service(domain, service, entity_id, data)
            
            result += "## ✅ Service Called Successfully\n\n"
            result += f"- **Service**: {domain}.{service}\n"
            
            if entity_id:
                result += f"- **Target**: {entity_id}\n"
            
            # Show context if available
            if isinstance(service_result, list) and service_result:
                result += f"- **Affected Entities**: {len(service_result)}\n"
            
            result += "\n## 💡 Next Steps\n\n"
            if entity_id:
                result += f"- Check state: `get_entity_state {entity_id}`\n"
            result += "- View all services: `get_services`\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_services":
            result = "# Home Assistant Services\n\n"
            
            services = await ha_client.get_services()
            
            if not services:
                result += "No services found.\n"
                return [TextContent(type="text", text=result)]
            
            result += f"Found services in {len(services)} domains\n\n"
            
            # Display services by domain
            for domain in sorted(services.keys()):
                domain_services = services[domain]
                result += f"## {domain.replace('_', ' ').title()}\n\n"
                
                for service_name, service_info in sorted(domain_services.items()):
                    description = service_info.get('description', 'No description')
                    result += f"### {domain}.{service_name}\n\n"
                    result += f"{description}\n\n"
                    
                    # Show fields if available
                    fields = service_info.get('fields', {})
                    if fields:
                        result += "**Parameters**:\n"
                        for field_name, field_info in fields.items():
                            field_desc = field_info.get('description', 'No description')
                            required = field_info.get('required', False)
                            req_marker = " (required)" if required else ""
                            result += f"- `{field_name}`{req_marker}: {field_desc}\n"
                        result += "\n"
            
            result += "## 💡 Usage\n\n"
            result += "Call a service with: `call_service <domain> <service> <entity_id> <data>`\n"
            result += "\nExample: `call_service light turn_on light.living_room {\"brightness\": 255}`\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_entity_history":
            entity_id = arguments.get("entity_id")
            start_time = arguments.get("start_time")
            end_time = arguments.get("end_time")
            
            if not entity_id:
                return [TextContent(type="text", text="Error: entity_id is required")]
            
            result = f"# Entity History: {entity_id}\n\n"
            
            # Get history
            history = await ha_client.get_entity_history(entity_id, start_time, end_time)
            
            if not history or not history[0]:
                result += "No history data found for this entity.\n"
                return [TextContent(type="text", text=result)]
            
            entity_history = history[0]  # History is returned as list of lists
            
            result += f"## Time Range\n\n"
            if start_time:
                result += f"- **Start**: {start_time}\n"
            else:
                result += "- **Start**: Last 24 hours\n"
            
            if end_time:
                result += f"- **End**: {end_time}\n"
            else:
                result += "- **End**: Now\n"
            
            result += f"\n## State Changes ({len(entity_history)} records)\n\n"
            
            # Show recent state changes (limit to 50)
            for i, state in enumerate(entity_history[:50]):
                timestamp = state.get('last_changed', state.get('last_updated', 'Unknown'))
                state_value = state.get('state', 'unknown')
                
                result += f"{i+1}. **{timestamp}**: {state_value}\n"
                
                # Show some key attributes if they changed
                attributes = state.get('attributes', {})
                if 'temperature' in attributes:
                    result += f"   - Temperature: {attributes['temperature']}\n"
                if 'brightness' in attributes:
                    result += f"   - Brightness: {attributes['brightness']}\n"
            
            if len(entity_history) > 50:
                result += f"\n... and {len(entity_history) - 50} more records\n"
            
            result += "\n## 💡 Analysis\n\n"
            
            # Simple statistics
            states = [s.get('state') for s in entity_history if s.get('state')]
            if states:
                unique_states = set(states)
                result += f"- **Unique States**: {len(unique_states)}\n"
                result += f"- **Most Recent**: {states[0]}\n"
                result += f"- **Oldest**: {states[-1]}\n"
            
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown entity tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing entity tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
