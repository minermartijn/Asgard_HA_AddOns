"""
Config addon tool handlers.
Extracted from addon_tools.py for better maintainability.
"""
import asyncio
import logging
from typing import Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)


async def handle_config_addon_tools(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle config addon tool execution."""
    try:
        if name == "get_addon_configuration":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            try:
                config = await ha_client.get_addon_configuration(addon_slug)
                
                result = f"# Configuration for {config.get('addon_name', addon_slug)}\n\n"
                result += f"**Addon Slug**: {config.get('addon_slug')}\n"
                result += f"**Has Configuration**: {'Yes' if config.get('has_configuration') else 'No'}\n\n"
                
                if not config.get('has_configuration'):
                    result += "ℹ️ This addon does not have configurable options.\n"
                    return [TextContent(type="text", text=result)]
                
                # Display current options
                options = config.get('options', {})
                if options:
                    result += "## Current Configuration\n\n"
                    result += "```json\n"
                    import json
                    result += json.dumps(options, indent=2)
                    result += "\n```\n\n"
                else:
                    result += "## Current Configuration\n\n"
                    result += "No options currently set (using defaults).\n\n"
                
                # Display schema if available
                schema = config.get('schema', {})
                if schema:
                    result += "## Available Options (Schema)\n\n"
                    result += "The following options can be configured:\n\n"
                    
                    # Parse schema to show available options
                    if isinstance(schema, dict):
                        for key, value in schema.items():
                            result += f"### `{key}`\n"
                            
                            if isinstance(value, dict):
                                # Show type if available
                                if 'type' in value:
                                    result += f"- **Type**: {value['type']}\n"
                                
                                # Show description if available
                                if 'description' in value:
                                    result += f"- **Description**: {value['description']}\n"
                                
                                # Show default if available
                                if 'default' in value:
                                    result += f"- **Default**: `{value['default']}`\n"
                                
                                # Show required status
                                if 'required' in value:
                                    result += f"- **Required**: {value['required']}\n"
                                
                                # Show enum values if available
                                if 'enum' in value:
                                    result += f"- **Allowed values**: {', '.join(map(str, value['enum']))}\n"
                            else:
                                result += f"- **Type**: {value}\n"
                            
                            result += "\n"
                    else:
                        result += "```json\n"
                        result += json.dumps(schema, indent=2)
                        result += "\n```\n\n"
                
                result += "## Usage\n\n"
                result += f"To update configuration, use:\n"
                result += f"```\nset_addon_configuration {addon_slug} {{'option_name': 'value'}}\n```\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                return [TextContent(type="text", text=f"Error: {str(ve)}")]
            except PermissionError as pe:
                return [TextContent(type="text", text=f"Permission Error: {str(pe)}")]
            except Exception as e:
                logger.error(f"Error getting addon configuration: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        elif name == "set_addon_configuration":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            options = arguments.get("options")
            if options is None:
                return [TextContent(type="text", text="Error: options parameter is required")]
            
            if not isinstance(options, dict):
                return [TextContent(type="text", text="Error: options must be a JSON object/dictionary")]
            
            boot = arguments.get("boot")
            network = arguments.get("network")
            
            try:
                result = f"# Updating Configuration for {addon_slug}\n\n"
                
                # Get current configuration for comparison
                result += "## Step 1: Getting current configuration...\n"
                try:
                    current_config = await ha_client.get_addon_configuration(addon_slug)
                    current_options = current_config.get('options', {})
                    addon_name = current_config.get('addon_name', addon_slug)
                    
                    result += f"✓ Current configuration retrieved for {addon_name}\n\n"
                    
                    # Show current values
                    if current_options:
                        result += "### Current Options:\n```json\n"
                        import json
                        result += json.dumps(current_options, indent=2)
                        result += "\n```\n\n"
                except Exception as e:
                    result += f"⚠ Could not retrieve current configuration: {e}\n\n"
                    addon_name = addon_slug
                
                # Show what will be changed
                result += "## Step 2: Applying new configuration...\n"
                result += "### New Options:\n```json\n"
                import json
                result += json.dumps(options, indent=2)
                result += "\n```\n"
                
                if boot:
                    result += f"\n**Boot Mode**: {boot}\n"
                if network:
                    result += f"\n**Network Configuration**: {json.dumps(network, indent=2)}\n"
                
                result += "\n"
                
                # Apply the configuration
                update_result = await ha_client.set_addon_configuration(
                    addon_slug, options, boot, network
                )
                
                result += f"✓ Configuration updated successfully\n\n"
                
                # Get updated configuration
                result += "## Step 3: Verifying changes...\n"
                try:
                    await asyncio.sleep(1)  # Brief wait for changes to apply
                    new_config = await ha_client.get_addon_configuration(addon_slug)
                    new_options = new_config.get('options', {})
                    
                    result += "### Updated Options:\n```json\n"
                    result += json.dumps(new_options, indent=2)
                    result += "\n```\n\n"
                    
                    # Show what changed
                    if current_options:
                        result += "### Changes Applied:\n"
                        for key, value in options.items():
                            old_value = current_options.get(key, "(not set)")
                            result += f"- `{key}`: `{old_value}` → `{value}`\n"
                        result += "\n"
                    
                except Exception as e:
                    result += f"⚠ Could not verify changes: {e}\n\n"
                
                # Restart recommendation
                result += "## Important Notes\n\n"
                result += "⚠️ **Configuration changes typically require an addon restart to take effect.**\n\n"
                result += "### Recommended Next Steps:\n"
                result += f"1. Restart the addon: `restart_addon {addon_slug}`\n"
                result += f"2. Check logs for any errors: `get_addon_logs {addon_slug}`\n"
                result += f"3. Verify addon is running: `get_addon_info {addon_slug}`\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                result = f"# Configuration Update Failed\n\n"
                result += f"❌ **Validation Error**: {str(ve)}\n\n"
                result += "**Possible reasons:**\n"
                result += "- Invalid option names or values\n"
                result += "- Options don't match the addon's schema\n"
                result += "- Required options are missing\n"
                result += "- Value types are incorrect (e.g., string instead of number)\n\n"
                result += "**Suggestions:**\n"
                result += f"- Use `get_addon_configuration {addon_slug}` to see available options and schema\n"
                result += "- Check the addon's documentation for valid configuration values\n"
                result += "- Ensure all required options are provided\n"
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = f"# Configuration Update Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = f"# Configuration Update Failed\n\n"
                result += f"❌ **Unexpected Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify the addon is installed and accessible\n"
                result += "- Try getting current configuration first to verify access\n"
                return [TextContent(type="text", text=result)]
        
        elif name == "validate_addon_configuration":
            addon_slug = arguments.get("addon_slug")
            if not addon_slug:
                return [TextContent(type="text", text="Error: addon_slug is required")]
            
            options = arguments.get("options")
            if options is None:
                return [TextContent(type="text", text="Error: options parameter is required")]
            
            if not isinstance(options, dict):
                return [TextContent(type="text", text="Error: options must be a JSON object/dictionary")]
            
            try:
                result = f"# Validating Configuration for {addon_slug}\n\n"
                
                # Show what we're validating
                result += "## Configuration to Validate\n\n"
                result += "```json\n"
                import json
                result += json.dumps(options, indent=2)
                result += "\n```\n\n"
                
                # Perform validation
                result += "## Validation Results\n\n"
                validation_result = await ha_client.validate_addon_configuration(addon_slug, options)
                
                if validation_result.get("valid"):
                    # Validation passed
                    result += "✅ **Configuration is Valid**\n\n"
                    result += "The provided configuration passes all validation checks and can be safely applied.\n\n"
                    
                    # Get current configuration to show what would change
                    try:
                        current_config = await ha_client.get_addon_configuration(addon_slug)
                        current_options = current_config.get('options', {})
                        addon_name = current_config.get('addon_name', addon_slug)
                        
                        result += f"### Addon: {addon_name}\n\n"
                        
                        # Show what would change
                        if current_options:
                            result += "### Changes that would be applied:\n"
                            changes_found = False
                            for key, new_value in options.items():
                                old_value = current_options.get(key, "(not set)")
                                if old_value != new_value:
                                    result += f"- `{key}`: `{old_value}` → `{new_value}`\n"
                                    changes_found = True
                                else:
                                    result += f"- `{key}`: `{new_value}` (unchanged)\n"
                            
                            if not changes_found:
                                result += "\nℹ️ No changes detected - all values match current configuration.\n"
                            result += "\n"
                        else:
                            result += "### New configuration values:\n"
                            for key, value in options.items():
                                result += f"- `{key}`: `{value}`\n"
                            result += "\n"
                    except Exception as e:
                        result += f"⚠ Could not retrieve current configuration for comparison: {e}\n\n"
                    
                    # Next steps
                    result += "## Next Steps\n\n"
                    result += "To apply this configuration:\n"
                    result += f"```\nset_addon_configuration {addon_slug} {json.dumps(options)}\n```\n\n"
                    result += "**Remember**: Configuration changes typically require an addon restart to take effect.\n"
                    
                else:
                    # Validation failed
                    result += "❌ **Configuration is Invalid**\n\n"
                    result += "The provided configuration has validation errors and cannot be applied.\n\n"
                    
                    # Show validation errors
                    errors = validation_result.get("errors", [])
                    if errors:
                        result += "### Validation Errors:\n\n"
                        for i, error in enumerate(errors, 1):
                            result += f"{i}. {error}\n"
                        result += "\n"
                    
                    # Provide suggestions
                    result += "## Troubleshooting Suggestions\n\n"
                    result += "**Common issues:**\n"
                    result += "- **Wrong data type**: Ensure values match expected types (string, number, boolean, etc.)\n"
                    result += "- **Missing required fields**: Check if all required options are provided\n"
                    result += "- **Invalid values**: Verify values are within allowed ranges or enum values\n"
                    result += "- **Unknown options**: Make sure option names match the addon's schema\n\n"
                    
                    result += "**How to fix:**\n"
                    result += f"1. Check the addon's schema: `get_addon_configuration {addon_slug}`\n"
                    result += "2. Review the validation errors above\n"
                    result += "3. Correct the configuration and validate again\n"
                    result += "4. Consult the addon's documentation for valid configuration examples\n"
                
                return [TextContent(type="text", text=result)]
                
            except ValueError as ve:
                result = f"# Validation Failed\n\n"
                result += f"❌ **Error**: {str(ve)}\n\n"
                result += "**Possible reasons:**\n"
                result += "- Addon not found or invalid addon slug\n"
                result += "- Addon does not support configuration validation\n"
                result += "- Invalid options format\n\n"
                result += "**Suggestions:**\n"
                result += f"- Verify the addon exists: `get_addon_info {addon_slug}`\n"
                result += f"- Check available options: `get_addon_configuration {addon_slug}`\n"
                result += "- Ensure options is a valid JSON object\n"
                return [TextContent(type="text", text=result)]
                
            except PermissionError as pe:
                result = f"# Validation Failed\n\n"
                result += f"❌ **Permission Error**: {str(pe)}\n\n"
                result += "**Required permissions:**\n"
                result += "- The MCP server needs Supervisor API access\n"
                result += "- Check that the addon has `supervisor_api: true` in config.yaml\n"
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                result = f"# Validation Failed\n\n"
                result += f"❌ **Unexpected Error**: {str(e)}\n\n"
                result += "**Troubleshooting:**\n"
                result += "- Check Home Assistant logs for more details\n"
                result += "- Verify the addon is installed and accessible\n"
                result += "- Ensure the validation endpoint is supported by this addon\n"
                return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown config tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing config tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
