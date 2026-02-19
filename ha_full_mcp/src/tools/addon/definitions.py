"""Tool definitions for addon management tools."""
from mcp.types import Tool


def get_addon_tool_definitions() -> list[Tool]:
    """Return all addon-related tool definitions."""
    return [
        Tool(
            name="list_addons",
            description="List all installed Home Assistant addons/apps with their status and details",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_addon_info",
            description="Get detailed information about a specific addon",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon (e.g., 'core_ssh', 'a0d7b954_vscode')",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="start_addon",
            description="Start a stopped addon",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to start",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="stop_addon",
            description="Stop a running addon",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to stop",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="restart_addon",
            description="Restart an addon",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to restart",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="get_addon_logs",
            description="Get the logs from an addon",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="update_addon",
            description="Check for updates and update an addon. This tool will: 1) Refresh update cache, 2) Check if update is available, 3) Update if available, 4) Start the addon, 5) Check logs for errors",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to update",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="install_addon",
            description="Install an addon from the Home Assistant add-on store. This tool installs add-ons by their slug identifier. The installation happens asynchronously - the tool returns immediately with job information while the installation continues in the background. Use get_addon_info to check installation status afterwards. Requires appropriate permissions to install add-ons.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to install (e.g., 'core_ssh', 'a0d7b954_vscode', 'core_mosquitto'). This must be a valid addon slug from the Home Assistant add-on store.",
                    },
                    "version": {
                        "type": "string",
                        "description": "Optional specific version to install (e.g., '9.7.1', '1.2.0'). If not specified, the latest available version will be installed.",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="uninstall_addon",
            description="⚠️ DESTRUCTIVE OPERATION: Uninstall an addon from Home Assistant. This permanently removes the addon and optionally its configuration data. The uninstallation happens asynchronously - the tool returns immediately with job information while the uninstallation continues in the background. Use get_addon_info to verify removal. WARNING: This action cannot be undone. All addon data will be lost unless you have backups.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to uninstall (e.g., 'core_ssh', 'a0d7b954_vscode'). The addon must be stopped before uninstallation.",
                    },
                    "remove_config": {
                        "type": "boolean",
                        "description": "Optional: If true, removes addon configuration data. If false or not specified, configuration is preserved for potential reinstallation. Default: false (keep config).",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="get_addon_configuration",
            description="Get the current configuration options and schema for an addon. Returns the addon's configuration settings, available options schema, and whether the addon has configurable options. Use this to view current settings before making changes with set_addon_configuration.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to get configuration for (e.g., 'core_ssh', 'a0d7b954_vscode')",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="set_addon_configuration",
            description="Set or update configuration options for an addon. This tool allows you to modify addon settings, boot mode, and network configuration. Configuration changes typically require an addon restart to take effect. The tool validates options against the addon's schema and provides before/after comparison.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to configure (e.g., 'core_ssh', 'a0d7b954_vscode')",
                    },
                    "options": {
                        "type": "object",
                        "description": "Configuration options to set as a JSON object. The structure depends on the addon's schema. Use get_addon_configuration to see available options and current values.",
                    },
                    "boot": {
                        "type": "string",
                        "description": "Optional boot mode: 'auto' (start automatically) or 'manual' (start manually). If not specified, boot mode remains unchanged.",
                        "enum": ["auto", "manual"],
                    },
                    "network": {
                        "type": "object",
                        "description": "Optional network configuration as a JSON object. Structure depends on addon requirements.",
                    },
                },
                "required": ["addon_slug", "options"],
            },
        ),
        Tool(
            name="validate_addon_configuration",
            description="Validate configuration options for an addon without applying them. This tool checks if the provided configuration is valid according to the addon's schema, helping you test configuration before committing changes. Returns detailed validation results including specific errors if validation fails. Use this before set_addon_configuration to ensure your configuration is correct.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to validate configuration for (e.g., 'core_ssh', 'a0d7b954_vscode')",
                    },
                    "options": {
                        "type": "object",
                        "description": "Configuration options to validate as a JSON object. The structure should match the addon's schema. Use get_addon_configuration to see the expected structure.",
                    },
                },
                "required": ["addon_slug", "options"],
            },
        ),
        Tool(
            name="rebuild_addon",
            description="Rebuild a local or custom addon from source. This tool rebuilds addons that have been modified or need to be recompiled. Only works with local/custom addons, not store addons. The rebuild process happens asynchronously and may take several minutes. Use this when: 1) Developing custom addons, 2) Addon source code has been modified, 3) Addon needs recompilation after system updates. Note: Store addons cannot be rebuilt - use update_addon instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the local/custom addon to rebuild (e.g., 'local_my_addon'). Must be a local or custom addon, not a store addon.",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="list_store_addons",
            description="List all available addons from the Home Assistant add-on store. This tool shows addons that can be installed, including their descriptions, versions, and installation status. Useful for discovering new addons or checking what's available before installation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Optional repository filter (e.g., 'core', 'local'). If specified, only shows addons from that repository.",
                    },
                    "search": {
                        "type": "string",
                        "description": "Optional search query to filter addons by name, description, or slug. Case-insensitive partial matching.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="reload_addons",
            description="Reload the addon list to refresh available addons. This is useful after adding a new repository or when the addon list needs to be refreshed without restarting Home Assistant. The operation is quick and does not affect running addons.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="check_addon_availability",
            description="Check if a specific addon is available for installation on this system. This verifies architecture compatibility, dependencies, and other requirements. Useful before attempting to install an addon to understand why it might not be available.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addon_slug": {
                        "type": "string",
                        "description": "The slug of the addon to check availability for (e.g., 'core_ssh', 'a0d7b954_vscode')",
                    },
                },
                "required": ["addon_slug"],
            },
        ),
        Tool(
            name="get_supervisor_logs",
            description="Get logs from the Home Assistant Supervisor. This is essential for debugging addon builds, installation issues, and system-level problems. Shows supervisor operations including addon installations, builds, updates, and system events.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_homeassistant_logs",
            description="Get logs from Home Assistant Core. This retrieves logs from the Home Assistant Core service, useful for debugging integration issues, automation problems, entity errors, and general Home Assistant errors. Shows startup messages, component loading, state changes, and error messages.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="restart_homeassistant",
            description="Restart Home Assistant Core. This restarts the Home Assistant Core service while keeping the Supervisor and addons running. Use this after configuration changes that require a restart. Note: This will temporarily disconnect all clients and integrations.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="read_config_file",
            description="Read a Home Assistant configuration file from the /config directory. Use this to view configuration files like configuration.yaml, scripts.yaml, secrets.yaml, automations.yaml, etc. Useful for reviewing current settings before making changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to read (e.g., 'configuration.yaml', 'scripts.yaml', 'secrets.yaml'). Must be a simple filename without path separators.",
                    },
                },
                "required": ["filename"],
            },
        ),
        Tool(
            name="write_config_file",
            description="Write content to a Home Assistant configuration file in the /config directory. Use this to update configuration files like configuration.yaml, scripts.yaml, secrets.yaml, etc. Automatically creates a timestamped backup before writing. After writing configuration files, you typically need to restart Home Assistant for changes to take effect.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to write (e.g., 'configuration.yaml', 'scripts.yaml', 'secrets.yaml'). Must be a simple filename without path separators.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file. Should be valid YAML, JSON, or appropriate format for the file type.",
                    },
                    "backup": {
                        "type": "boolean",
                        "description": "If true, creates a timestamped backup of the existing file before writing. Default: true. Backups are saved as .backup_<filename>.<timestamp> in the /config directory.",
                    },
                },
                "required": ["filename", "content"],
            },
        ),
        Tool(
            name="check_config",
            description="Validate the Home Assistant configuration without restarting. This checks configuration.yaml and related files for errors before applying changes. Always use this before restarting Home Assistant after configuration changes to avoid breaking your installation.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]
