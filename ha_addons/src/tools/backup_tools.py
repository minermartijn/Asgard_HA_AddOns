"""Narrow backup and restore tools for lifeboat recovery."""

import logging
from typing import Any

from mcp.types import TextContent, Tool

logger = logging.getLogger(__name__)


def get_backup_tool_definitions() -> list[Tool]:
    """Return lifeboat backup tools; destructive deletion is intentionally absent."""
    return [
        Tool(name="create_addon_backup", description="Create a partial Home Assistant backup containing exactly one addon before maintenance or recovery.", inputSchema={"type": "object", "properties": {"addon_slug": {"type": "string", "description": "Exact installed addon slug"}, "name": {"type": "string", "description": "Optional backup name"}, "password": {"type": "string", "description": "Optional encryption password"}}, "required": ["addon_slug"]}),
        Tool(name="list_backups", description="List available Home Assistant backups and their safe metadata.", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="get_backup_info", description="Inspect one backup, including the addons it contains, before any restore.", inputSchema={"type": "object", "properties": {"backup_slug": {"type": "string", "description": "Backup slug/ID"}}, "required": ["backup_slug"]}),
        Tool(name="restore_addon_backup", description="DISRUPTIVE: restore exactly one addon from a verified backup. Refuses if backup metadata does not include the exact addon slug.", inputSchema={"type": "object", "properties": {"backup_slug": {"type": "string", "description": "Backup slug/ID"}, "addon_slug": {"type": "string", "description": "Exact addon slug to restore"}, "password": {"type": "string", "description": "Required when the backup is encrypted"}}, "required": ["backup_slug", "addon_slug"]}),
    ]


def _addon_slugs(backup: dict[str, Any]) -> list[str]:
    content = backup.get("content") or {}
    raw = content.get("addons", backup.get("addons", []))
    return sorted(str(item.get("slug") if isinstance(item, dict) else item) for item in raw if (item.get("slug") if isinstance(item, dict) else item))


async def handle_backup_tool(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Execute a lifeboat backup tool without echoing secrets."""
    try:
        if name == "create_addon_backup":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            created = await ha_client.create_addon_backup(addon_slug, arguments.get("name"), arguments.get("password"))
            text = (f"Addon backup initiated for `{addon_slug}`.\n\n- Backup slug: `{created.get('slug') or 'pending'}`\n- Job ID: `{created.get('job_id') or 'not provided'}`\n- Encrypted: {'yes' if created.get('protected') else 'no'}\n\nUse `get_backup_info` to verify the completed backup includes the exact addon before relying on it.")
            return [TextContent(type="text", text=text)]
        if name == "list_backups":
            backups = await ha_client.list_backups()
            if not backups:
                return [TextContent(type="text", text="No backups found.")]
            lines = [f"Available backups: {len(backups)}"]
            for backup in backups:
                lines.append(f"- `{backup.get('slug', 'unknown')}` — {backup.get('name', 'Unnamed')} ({backup.get('type', 'unknown')}, protected: {'yes' if backup.get('protected') else 'no'})")
            return [TextContent(type="text", text="\n".join(lines))]
        if name == "get_backup_info":
            backup_slug = arguments.get("backup_slug")
            if not backup_slug:
                return [TextContent(type="text", text="Error: backup_slug is required")]
            backup = await ha_client.get_backup_info(backup_slug)
            addons = _addon_slugs(backup)
            text = (f"Backup `{backup_slug}`: {backup.get('name', 'Unnamed')}\n\n- Type: {backup.get('type', 'unknown')}\n- Protected: {'yes' if backup.get('protected') else 'no'}\n- Addons: {', '.join(f'`{slug}`' for slug in addons) if addons else 'none reported'}")
            return [TextContent(type="text", text=text)]
        if name == "restore_addon_backup":
            backup_slug, addon_slug = arguments.get("backup_slug"), arguments.get("addon_slug")
            if not backup_slug or not addon_slug:
                return [TextContent(type="text", text="Error: backup_slug and addon_slug are required")]
            restored = await ha_client.restore_addon_backup(backup_slug, addon_slug, arguments.get("password"))
            text = (f"Restore initiated for addon `{addon_slug}` from backup `{backup_slug}`.\n\n- Job ID: `{restored.get('job_id') or 'not provided'}`\n\nThe operation may be asynchronous. Verify addon version, state, and logs independently before declaring recovery successful.")
            return [TextContent(type="text", text=text)]
        return [TextContent(type="text", text=f"Unknown backup tool: {name}")]
    except Exception as exc:
        logger.error("Error executing backup tool %s: %s", name, exc)
        return [TextContent(type="text", text=f"Error: {exc}")]
