"""Read-only area, device, and config-entry inventory tools."""

from typing import Any

from mcp.types import TextContent, Tool


def get_inventory_tool_definitions() -> list[Tool]:
    """Return inventory tool definitions."""
    return [
        Tool(
            name="list_areas",
            description="List Home Assistant areas with their IDs, names, floors, aliases, and labels.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_devices",
            description="List registered Home Assistant devices. Optionally filter by area ID or config-entry ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "area_id": {"type": "string", "description": "Optional area ID"},
                    "config_entry_id": {
                        "type": "string",
                        "description": "Optional config-entry ID",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="list_config_entries",
            description="List Home Assistant config entries and their load states. Optionally filter by integration domain or state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Optional integration domain"},
                    "state": {
                        "type": "string",
                        "description": "Optional load state such as loaded, setup_error, or not_loaded",
                    },
                },
                "required": [],
            },
        ),
    ]


def _value(value: Any, fallback: str = "—") -> str:
    """Render optional registry values consistently."""
    return str(value) if value not in (None, "", []) else fallback


def _device_config_entries(device: dict[str, Any]) -> list[str]:
    """Normalize old and new Home Assistant device registry shapes."""
    entries = device.get("config_entries")
    if entries:
        return entries
    entry = device.get("config_entry_id")
    return [entry] if entry else []


async def handle_inventory_tool(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle inventory tool execution."""
    try:
        if name == "list_areas":
            areas = await ha_client.list_areas()
            lines = ["# Home Assistant Areas", "", f"Found {len(areas)} area(s).", ""]
            for area in sorted(areas, key=lambda item: (item.get("name") or "").casefold()):
                lines.extend([
                    f"- **{_value(area.get('name'), 'Unnamed area')}** (`{_value(area.get('area_id'))}`)",
                    f"  - Floor: {_value(area.get('floor_id'))}",
                    f"  - Aliases: {_value(', '.join(area.get('aliases') or []))}",
                    f"  - Labels: {_value(', '.join(area.get('labels') or []))}",
                ])
        elif name == "list_devices":
            area_id = arguments.get("area_id")
            config_entry_id = arguments.get("config_entry_id")
            devices = await ha_client.list_devices(area_id, config_entry_id)
            lines = ["# Home Assistant Devices", "", f"Found {len(devices)} device(s).", ""]
            for device in sorted(devices, key=lambda item: (item.get("name_by_user") or item.get("name") or "").casefold()):
                lines.extend([
                    f"- **{_value(device.get('name_by_user') or device.get('name'), 'Unnamed device')}** (`{_value(device.get('id'))}`)",
                    f"  - Area: {_value(device.get('area_id'))}",
                    f"  - Manufacturer / model: {_value(device.get('manufacturer'))} / {_value(device.get('model'))}",
                    f"  - Config entries: {_value(', '.join(_device_config_entries(device)))}",
                    f"  - Disabled by: {_value(device.get('disabled_by'))}",
                ])
        elif name == "list_config_entries":
            domain = arguments.get("domain")
            state = arguments.get("state")
            entries = await ha_client.list_config_entries(domain, state)
            lines = ["# Home Assistant Config Entries", "", f"Found {len(entries)} config entr{'y' if len(entries) == 1 else 'ies'}.", ""]
            for entry in sorted(entries, key=lambda item: (item.get("domain") or "", item.get("title") or "")):
                lines.extend([
                    f"- **{_value(entry.get('title'), 'Untitled')}** (`{_value(entry.get('entry_id'))}`)",
                    f"  - Domain: {_value(entry.get('domain'))}",
                    f"  - State: {_value(entry.get('state'))}",
                    f"  - Source: {_value(entry.get('source'))}",
                    f"  - Disabled by: {_value(entry.get('disabled_by'))}",
                ])
        else:
            return [TextContent(type="text", text=f"Unknown inventory tool: {name}")]

        return [TextContent(type="text", text="\n".join(lines) + "\n")]
    except Exception as exc:
        return [TextContent(type="text", text=f"Error executing {name}: {exc}")]
