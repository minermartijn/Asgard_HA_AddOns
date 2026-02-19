"""
Configuration file tool handlers.
Extracted from system_handlers.py for better maintainability.
"""
import logging
from typing import Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)


async def handle_config_file_addon_tools(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle config file addon tool execution."""
    try:
        if name == "read_config_file":
            filename = arguments.get("filename")
            if not filename:
                return [TextContent(type="text", text="Error: filename is required")]
            
            try:
                result = f"# Reading Configuration File: {filename}\n\n"
                
                # Read the file
                content = await ha_client.read_config_file(filename)
                
                # Display file info
                lines = content.split('\n')
                result += f"**File**: {filename}\n"
                result += f"**Size**: {len(content)} bytes\n"
                result += f"**Lines**: {len(lines)}\n\n"
                
                # Display content
                result += "## File Contents\n\n"
                result += "```yaml\n"
                result += content
                result += "\n```\n\n"
                
                # Provide usage tips
                result += "## Usage Tips\n\n"
                result += "**To edit this file:**\n"
                result += f"1. Make your changes to the content\n"
                result += f"2. Use `write_config_file` to save changes\n"
                result += f"3. Restart Home Assistant if needed: `restart_homeassistant`\n\n"
                
                result += "**Common files:**\n"
                result += "- `configuration.yaml` - Main Home Assistant configuration\n"
                result += "- `scripts.yaml` - Script definitions\n"
                result += "- `secrets.yaml` - Sensitive data (passwords, tokens)\n"
                result += "- `automations.yaml` - Automation definitions\n"
                result += "- `scenes.yaml` - Scene definitions\n"
                result += "- `groups.yaml` - Group definitions\n"
                
                return [TextContent(type="text", text=result)]
                
            except FileNotFoundError as fnf:
                result = f"# File Not Found\n\n"
                result += f"❌ **Error**: {str(fnf)}\n\n"
                result += "**Possible reasons:**\n"
                result += f"- File '{filename}' doesn't exist in /config directory\n"
                result += "- Filename is misspelled\n"
                result += "- File is in a subdirectory (use full filename with extension)\n\n"
                result += "**Common configuration files:**\n"
                result += "- configuration.yaml\n"
                result += "- scripts.yaml\n"
                result += "- secrets.yaml\n"
                result += "- automations.yaml\n"
                result += "- scenes.yaml\n"
                result += "- groups.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                result = f"# Invalid Filename\n\n"
                result += f"❌ **Error**: {str(ve)}\n\n"
                result += "**Security note:**\n"
                result += "- Filenames must not contain path separators (/, \\)\n"
                result += "- Filenames must not contain '..' (path traversal)\n"
                result += "- Use simple filenames only (e.g., 'configuration.yaml')\n"
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = f"# Permission Denied\n\n"
                result += f"❌ **Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The addon needs access to the /config directory\n"
                result += "- Check that 'config:rw' is in the addon's map configuration\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = f"# Read Failed\n\n"
                result += f"❌ **Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Verify the file exists and is readable\n"
                result += "- Check file permissions\n"
                result += "- Ensure the file is not corrupted\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "write_config_file":
            filename = arguments.get("filename")
            if not filename:
                return [TextContent(type="text", text="Error: filename is required")]
            
            content = arguments.get("content")
            if content is None:
                return [TextContent(type="text", text="Error: content is required")]
            
            backup = arguments.get("backup", True)
            
            try:
                import json
                import yaml
                
                result = f"# Writing Configuration File: {filename}\n\n"
                
                # Show what will be written
                result += "## Content to Write\n\n"
                result += f"**File**: {filename}\n"
                result += f"**Size**: {len(content)} bytes\n"
                result += f"**Lines**: {len(content.split(chr(10)))}\n"
                result += f"**Backup**: {'Yes' if backup else 'No'}\n\n"
                
                # Validate YAML if it's a YAML file
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    result += "## Validating YAML Syntax\n\n"
                    try:
                        yaml.safe_load(content)
                        result += "✓ YAML syntax is valid\n\n"
                    except yaml.YAMLError as yaml_error:
                        result += f"⚠️ **YAML Syntax Warning**: {str(yaml_error)}\n\n"
                        result += "The content has YAML syntax errors. Writing anyway, but Home Assistant may fail to load this file.\n\n"
                
                # Preview content (first 20 lines)
                lines = content.split('\n')
                preview_lines = lines[:20] if len(lines) > 20 else lines
                result += "### Content Preview (first 20 lines):\n```yaml\n"
                result += "\n".join(preview_lines)
                if len(lines) > 20:
                    result += f"\n... ({len(lines) - 20} more lines)"
                result += "\n```\n\n"
                
                # Write the file
                result += "## Writing File\n\n"
                write_result = await ha_client.write_config_file(filename, content, backup)
                
                result += f"✓ **File written successfully**\n\n"
                result += f"- **Bytes written**: {write_result.get('bytes_written', 0)}\n"
                result += f"- **Path**: {write_result.get('path', 'N/A')}\n"
                
                if write_result.get('backup_created'):
                    result += f"- **Backup created**: {write_result.get('backup_path', 'Yes')}\n"
                else:
                    result += f"- **Backup**: No backup created\n"
                
                result += "\n"
                
                # Important next steps
                result += "## ⚠️ Important Next Steps\n\n"
                
                if filename in ['configuration.yaml', 'scripts.yaml', 'automations.yaml', 'scenes.yaml', 'groups.yaml']:
                    result += "**Configuration changes require a restart:**\n\n"
                    result += "1. **Check configuration** (recommended):\n"
                    result += "   - Go to Developer Tools > YAML in Home Assistant UI\n"
                    result += "   - Click 'Check Configuration' to validate\n"
                    result += "   - Fix any errors before restarting\n\n"
                    result += "2. **Restart Home Assistant**:\n"
                    result += "   ```\n"
                    result += "   restart_homeassistant\n"
                    result += "   ```\n\n"
                    result += "3. **Monitor logs** after restart:\n"
                    result += "   ```\n"
                    result += "   get_homeassistant_logs\n"
                    result += "   ```\n\n"
                
                if filename == 'secrets.yaml':
                    result += "**Secrets file updated:**\n"
                    result += "- Secrets are loaded at startup\n"
                    result += "- Restart Home Assistant to use new secrets\n"
                    result += "- Keep this file secure and backed up\n\n"
                
                result += "## Backup Information\n\n"
                if write_result.get('backup_created'):
                    result += f"A backup of the original file was created:\n"
                    result += f"- **Location**: {write_result.get('backup_path', 'N/A')}\n"
                    result += f"- You can restore from this backup if needed\n"
                else:
                    result += "No backup was created (either disabled or file didn't exist).\n"
                
                result += "\n## Safety Tips\n\n"
                result += "- Always check configuration before restarting\n"
                result += "- Keep backups of working configurations\n"
                result += "- Test changes in a development environment first\n"
                result += "- Use version control (git) for configuration files\n"
                result += "- Document your changes for future reference\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                result = f"# Invalid Input\n\n"
                result += f"❌ **Error**: {str(ve)}\n\n"
                result += "**Common issues:**\n"
                result += "- Invalid filename (contains path separators or '..')\n"
                result += "- Content is None or invalid\n"
                result += "- Use simple filenames only (e.g., 'configuration.yaml')\n"
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = f"# Permission Denied\n\n"
                result += f"❌ **Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The addon needs write access to the /config directory\n"
                result += "- Check that 'config:rw' is in the addon's map configuration\n"
                result += "- Verify file permissions in the /config directory\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = f"# Write Failed\n\n"
                result += f"❌ **Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check available disk space\n"
                result += "- Verify write permissions\n"
                result += "- Ensure the /config directory is accessible\n"
                result += "- Check if the file is locked by another process\n\n"
                
                if backup:
                    result += "**Note**: If a backup was created, the original file is preserved.\n"
                
                return [TextContent(type="text", text=result)]
        
        elif name == "check_config":
            try:
                result = "# Checking Home Assistant Configuration\n\n"
                
                result += "⏳ **Validating configuration files...**\n\n"
                result += "This will check:\n"
                result += "- configuration.yaml\n"
                result += "- All included files (scripts.yaml, automations.yaml, etc.)\n"
                result += "- Integration configurations\n"
                result += "- Template syntax\n"
                result += "- YAML syntax\n\n"
                
                # Perform configuration check
                check_result = await ha_client.check_config()
                
                is_valid = check_result.get("valid", False)
                errors = check_result.get("errors")
                
                if is_valid:
                    # Configuration is valid
                    result += "## ✅ Configuration is Valid\n\n"
                    result += "Your Home Assistant configuration has been validated successfully!\n\n"
                    result += "**All checks passed:**\n"
                    result += "- ✓ YAML syntax is correct\n"
                    result += "- ✓ All integrations are properly configured\n"
                    result += "- ✓ Templates are valid\n"
                    result += "- ✓ No configuration errors detected\n\n"
                    
                    result += "## Safe to Restart\n\n"
                    result += "Your configuration is valid and it's safe to restart Home Assistant.\n\n"
                    result += "**To apply changes:**\n"
                    result += "```\n"
                    result += "restart_homeassistant\n"
                    result += "```\n\n"
                    
                    result += "**Or restart from the UI:**\n"
                    result += "- Go to Developer Tools > YAML\n"
                    result += "- Click 'Restart' button\n"
                    
                else:
                    # Configuration has errors
                    result += "## ❌ Configuration Has Errors\n\n"
                    result += "⚠️ **DO NOT RESTART HOME ASSISTANT**\n\n"
                    result += "Your configuration has errors that must be fixed before restarting.\n"
                    result += "Restarting with these errors may prevent Home Assistant from starting.\n\n"
                    
                    if errors:
                        result += "### Configuration Errors:\n\n"
                        if isinstance(errors, str):
                            result += f"```\n{errors}\n```\n\n"
                        elif isinstance(errors, list):
                            for i, error in enumerate(errors, 1):
                                result += f"{i}. {error}\n"
                            result += "\n"
                        elif isinstance(errors, dict):
                            import json
                            result += "```json\n"
                            result += json.dumps(errors, indent=2)
                            result += "\n```\n\n"
                    
                    result += "## How to Fix\n\n"
                    result += "1. **Review the errors above** - They usually indicate:\n"
                    result += "   - YAML syntax errors (indentation, colons, quotes)\n"
                    result += "   - Missing required configuration options\n"
                    result += "   - Invalid values for configuration options\n"
                    result += "   - Unknown integration or platform names\n\n"
                    
                    result += "2. **Edit the configuration file:**\n"
                    result += "   ```\n"
                    result += "   read_config_file configuration.yaml\n"
                    result += "   ```\n\n"
                    
                    result += "3. **Fix the errors** and save the file\n\n"
                    
                    result += "4. **Check configuration again:**\n"
                    result += "   ```\n"
                    result += "   check_config\n"
                    result += "   ```\n\n"
                    
                    result += "5. **Only restart when validation passes**\n\n"
                    
                    result += "## Common Issues\n\n"
                    result += "- **Indentation errors**: YAML requires consistent spacing (use 2 spaces)\n"
                    result += "- **Missing colons**: Each key must have a colon (key: value)\n"
                    result += "- **Quotes**: Use quotes for strings with special characters\n"
                    result += "- **Duplicate keys**: Each key can only appear once in a section\n"
                    result += "- **Invalid references**: Check !include and !secret references\n"
                
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = "# Configuration Check Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Home Assistant Core API access\n"
                result += "- Check that the addon has `homeassistant_api: true` in config.yaml\n"
                result += "- Verify the HA token is configured correctly\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = "# Configuration Check Failed\n\n"
                result += f"❌ **Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Verify Home Assistant Core is running\n"
                result += "- Check that the Core API is accessible\n"
                result += "- Ensure the MCP server has proper API access\n"
                result += "- Try checking configuration from the Home Assistant UI\n"
                return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown config file tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing config file tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
