"""Backup management tools for Home Assistant MCP Server."""
import asyncio
import logging
from typing import Any
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)


def get_backup_tool_definitions() -> list[Tool]:
    """Return all backup-related tool definitions."""
    return [
        Tool(
            name="create_backup",
            description="Create a full or partial backup of Home Assistant. Backups include configuration, addons, and data. Can create full system backups or partial backups of specific components.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the backup (e.g., 'Before Update', 'Daily Backup')",
                    },
                    "password": {
                        "type": "string",
                        "description": "Optional password to encrypt the backup for security",
                    },
                    "addons": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of addon slugs to include in partial backup. If omitted, creates full backup.",
                    },
                    "folders": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of folders to include: 'homeassistant', 'ssl', 'share', 'addons/local', 'media'. If omitted, includes all.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="list_backups",
            description="List all available backups with their details including size, date, type (full/partial), and what's included. Useful for finding backups to restore or manage.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_backup_info",
            description="Get detailed information about a specific backup including size, creation date, included addons and folders, whether it's encrypted, and restore compatibility.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "The backup slug/ID to get information about",
                    },
                },
                "required": ["slug"],
            },
        ),
        Tool(
            name="restore_backup",
            description="Restore Home Assistant from a backup. Can restore full system or partial components. WARNING: This will restart Home Assistant and may take several minutes. Ensure you have the correct backup slug.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "The backup slug/ID to restore from",
                    },
                    "password": {
                        "type": "string",
                        "description": "Password if the backup is encrypted",
                    },
                    "addons": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of addon slugs to restore from partial backup. If omitted, restores all.",
                    },
                    "folders": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of folders to restore. If omitted, restores all.",
                    },
                },
                "required": ["slug"],
            },
        ),
        Tool(
            name="delete_backup",
            description="Delete a backup to free up storage space. WARNING: This permanently removes the backup file and cannot be undone. Make sure you have other backups before deleting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "The backup slug/ID to delete",
                    },
                },
                "required": ["slug"],
            },
        ),
    ]


async def handle_backup_tool(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle backup tool execution."""
    try:
        if name == "create_backup":
            backup_name = arguments.get("name", "MCP Backup")
            password = arguments.get("password")
            addons = arguments.get("addons")
            folders = arguments.get("folders")
            
            result = f"# Creating Backup: {backup_name}\n\n"
            
            # Determine backup type
            is_partial = addons is not None or folders is not None
            backup_type = "Partial" if is_partial else "Full"
            
            result += f"**Backup Type**: {backup_type}\n"
            result += f"**Name**: {backup_name}\n"
            result += f"**Encrypted**: {'Yes' if password else 'No'}\n\n"
            
            if is_partial:
                result += "## Backup Contents\n\n"
                if addons:
                    result += f"**Addons**: {', '.join(addons)}\n"
                if folders:
                    result += f"**Folders**: {', '.join(folders)}\n"
                result += "\n"
            
            result += "⏳ **Creating backup...**\n\n"
            result += "This may take several minutes depending on the size of your system.\n\n"
            
            # Create the backup
            backup_result = await ha_client.create_backup(
                name=backup_name,
                password=password,
                addons=addons,
                folders=folders
            )
            
            result += "## ✅ Backup Created Successfully\n\n"
            result += f"- **Backup Slug**: {backup_result.get('slug')}\n"
            result += f"- **Size**: {backup_result.get('size', 'Unknown')} MB\n"
            result += f"- **Location**: {backup_result.get('location', 'Local')}\n"
            
            if backup_result.get('job_id'):
                result += f"- **Job ID**: {backup_result['job_id']}\n"
            
            result += "\n## 💡 Next Steps\n\n"
            result += "- Backup is stored locally on your Home Assistant system\n"
            result += "- You can download it from Settings → System → Backups\n"
            result += "- Consider storing a copy off-site for disaster recovery\n"
            result += f"- To restore this backup, use: `restore_backup {backup_result.get('slug')}`\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "list_backups":
            result = "# Home Assistant Backups\n\n"
            
            backups = await ha_client.list_backups()
            
            if not backups:
                result += "No backups found.\n\n"
                result += "## Create Your First Backup\n\n"
                result += "```\ncreate_backup \"My First Backup\"\n```\n"
                return [TextContent(type="text", text=result)]
            
            result += f"Found {len(backups)} backup(s)\n\n"
            
            # Sort by date (newest first)
            sorted_backups = sorted(backups, key=lambda x: x.get('date', ''), reverse=True)
            
            for backup in sorted_backups:
                result += f"## {backup.get('name', 'Unnamed Backup')}\n\n"
                result += f"- **Slug**: `{backup.get('slug')}`\n"
                result += f"- **Date**: {backup.get('date', 'Unknown')}\n"
                result += f"- **Type**: {backup.get('type', 'Unknown').title()}\n"
                result += f"- **Size**: {backup.get('size', 0):.2f} MB\n"
                result += f"- **Protected**: {'Yes' if backup.get('protected') else 'No'}\n"
                
                # Show what's included
                if backup.get('content'):
                    content = backup['content']
                    included = []
                    if content.get('homeassistant'):
                        included.append("Home Assistant config")
                    if content.get('addons'):
                        addon_count = len(content['addons'])
                        included.append(f"{addon_count} addon(s)")
                    if content.get('folders'):
                        folder_count = len(content['folders'])
                        included.append(f"{folder_count} folder(s)")
                    
                    if included:
                        result += f"- **Includes**: {', '.join(included)}\n"
                
                result += "\n"
            
            result += "## 💡 Quick Actions\n\n"
            result += "- Get details: `get_backup_info <slug>`\n"
            result += "- Restore: `restore_backup <slug>`\n"
            result += "- Delete: `delete_backup <slug>`\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_backup_info":
            slug = arguments.get("slug")
            if not slug:
                return [TextContent(type="text", text="Error: backup slug is required")]
            
            result = f"# Backup Information: {slug}\n\n"
            
            backup_info = await ha_client.get_backup_info(slug)
            
            result += f"## {backup_info.get('name', 'Unnamed Backup')}\n\n"
            
            # Basic info
            result += "### Basic Information\n\n"
            result += f"- **Slug**: `{backup_info.get('slug')}`\n"
            result += f"- **Date Created**: {backup_info.get('date', 'Unknown')}\n"
            result += f"- **Type**: {backup_info.get('type', 'Unknown').title()}\n"
            result += f"- **Size**: {backup_info.get('size', 0):.2f} MB\n"
            result += f"- **Protected**: {'Yes (encrypted)' if backup_info.get('protected') else 'No'}\n"
            result += f"- **Location**: {backup_info.get('location', 'Local')}\n\n"
            
            # Content details
            if backup_info.get('content'):
                content = backup_info['content']
                result += "### Backup Contents\n\n"
                
                if content.get('homeassistant'):
                    result += "**✓ Home Assistant Configuration**\n"
                    result += "  - configuration.yaml and all config files\n"
                    result += "  - Integrations and entities\n\n"
                
                if content.get('addons'):
                    addons = content['addons']
                    result += f"**✓ Addons ({len(addons)})**\n"
                    for addon in addons[:10]:  # Show first 10
                        result += f"  - {addon.get('name', addon.get('slug', 'Unknown'))}\n"
                    if len(addons) > 10:
                        result += f"  - ... and {len(addons) - 10} more\n"
                    result += "\n"
                
                if content.get('folders'):
                    folders = content['folders']
                    result += f"**✓ Folders ({len(folders)})**\n"
                    for folder in folders:
                        result += f"  - {folder}\n"
                    result += "\n"
            
            # System info
            if backup_info.get('homeassistant'):
                result += "### System Information\n\n"
                result += f"- **HA Version**: {backup_info['homeassistant']}\n"
            
            if backup_info.get('supervisor'):
                result += f"- **Supervisor Version**: {backup_info['supervisor']}\n"
            
            result += "\n## 💡 Actions\n\n"
            result += f"- Restore this backup: `restore_backup {slug}`\n"
            result += f"- Delete this backup: `delete_backup {slug}`\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "restore_backup":
            slug = arguments.get("slug")
            if not slug:
                return [TextContent(type="text", text="Error: backup slug is required")]
            
            password = arguments.get("password")
            addons = arguments.get("addons")
            folders = arguments.get("folders")
            
            result = f"# Restoring Backup: {slug}\n\n"
            
            result += "⚠️ **WARNING: SYSTEM RESTORE IN PROGRESS**\n\n"
            result += "This will:\n"
            result += "- Restart Home Assistant\n"
            result += "- Restore configuration and data from the backup\n"
            result += "- Take several minutes to complete\n"
            result += "- Temporarily disconnect all clients\n\n"
            
            # Show what will be restored
            is_partial = addons is not None or folders is not None
            if is_partial:
                result += "## Partial Restore\n\n"
                if addons:
                    result += f"**Restoring Addons**: {', '.join(addons)}\n"
                if folders:
                    result += f"**Restoring Folders**: {', '.join(folders)}\n"
                result += "\n"
            else:
                result += "## Full System Restore\n\n"
                result += "Restoring all components from backup.\n\n"
            
            result += "⏳ **Initiating restore...**\n\n"
            
            # Restore the backup
            restore_result = await ha_client.restore_backup(
                slug=slug,
                password=password,
                addons=addons,
                folders=folders
            )
            
            result += "## ✅ Restore Initiated\n\n"
            result += f"- **Status**: {restore_result.get('result', 'ok')}\n"
            
            if restore_result.get('job_id'):
                result += f"- **Job ID**: {restore_result['job_id']}\n"
            
            result += "\n## ⏳ What Happens Next\n\n"
            result += "1. **Home Assistant will restart** (30-60 seconds)\n"
            result += "2. **Backup data will be restored** (2-10 minutes)\n"
            result += "3. **Services will reload** (1-2 minutes)\n"
            result += "4. **System will be ready** (check UI for availability)\n\n"
            
            result += "## 💡 After Restore\n\n"
            result += "- Wait for Home Assistant to become available\n"
            result += "- Check that all integrations are working\n"
            result += "- Verify automations are running\n"
            result += "- Check addon logs if any issues occur\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "delete_backup":
            slug = arguments.get("slug")
            if not slug:
                return [TextContent(type="text", text="Error: backup slug is required")]
            
            result = f"# Deleting Backup: {slug}\n\n"
            
            # Get backup info first
            try:
                backup_info = await ha_client.get_backup_info(slug)
                result += f"## {backup_info.get('name', 'Unnamed Backup')}\n\n"
                result += f"- **Date**: {backup_info.get('date', 'Unknown')}\n"
                result += f"- **Size**: {backup_info.get('size', 0):.2f} MB\n"
                result += f"- **Type**: {backup_info.get('type', 'Unknown').title()}\n\n"
            except Exception:
                result += "⚠️ Could not retrieve backup information\n\n"
            
            result += "⚠️ **WARNING: PERMANENT DELETION**\n\n"
            result += "This action cannot be undone. The backup file will be permanently removed.\n\n"
            
            # Delete the backup
            delete_result = await ha_client.delete_backup(slug)
            
            result += "## ✅ Backup Deleted\n\n"
            result += f"- **Status**: {delete_result.get('result', 'ok')}\n"
            result += f"- **Backup**: {slug}\n\n"
            
            result += "## 💡 Storage Freed\n\n"
            result += "The backup has been removed and storage space has been freed.\n"
            result += "You can create a new backup anytime with `create_backup`.\n"
            
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown backup tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing backup tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
