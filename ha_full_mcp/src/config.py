"""
Configuration management for Home Assistant MCP Server.
"""

import os
import secrets
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Server configuration."""
    ha_token: str
    api_key: str
    transport_type: str
    host: str
    port: int
    enabled_tools: list[str]
    server_name: str = "home-assistant-mcp"
    server_version: str = "1.8.0"


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


def load_config() -> ServerConfig:
    """Load configuration from environment variables."""
    # Get configuration from environment
    ha_token = os.environ.get("HA_TOKEN")
    api_key = os.environ.get("API_KEY", "").strip()
    transport_type = os.environ.get("TRANSPORT", "sse").lower()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8010"))
    
    # Define all available tools with their environment variable names
    # Now using nested structure: SECTION_TOOL_NAME
    all_tools = {
        # Addon Information Tools
        "list_addons": "ADDON_INFORMATION_LIST_ADDONS",
        "get_addon_info": "ADDON_INFORMATION_GET_ADDON_INFO",
        "get_addon_logs": "ADDON_INFORMATION_GET_ADDON_LOGS",
        # Addon Control Tools
        "start_addon": "ADDON_CONTROL_START_ADDON",
        "stop_addon": "ADDON_CONTROL_STOP_ADDON",
        "restart_addon": "ADDON_CONTROL_RESTART_ADDON",
        # Addon Management Tools
        "update_addon": "ADDON_MANAGEMENT_UPDATE_ADDON",
        "install_addon": "ADDON_MANAGEMENT_INSTALL_ADDON",
        "uninstall_addon": "ADDON_MANAGEMENT_UNINSTALL_ADDON",
        # Addon Configuration Tools
        "get_addon_configuration": "ADDON_CONFIGURATION_GET_ADDON_CONFIGURATION",
        "set_addon_configuration": "ADDON_CONFIGURATION_SET_ADDON_CONFIGURATION",
        "validate_addon_configuration": "ADDON_CONFIGURATION_VALIDATE_ADDON_CONFIGURATION",
        # Addon Advanced Tools
        "rebuild_addon": "ADDON_ADVANCED_REBUILD_ADDON",
        "list_store_addons": "ADDON_ADVANCED_LIST_STORE_ADDONS",
        "reload_addons": "ADDON_ADVANCED_RELOAD_ADDONS",
        "check_addon_availability": "ADDON_ADVANCED_CHECK_ADDON_AVAILABILITY",
        # System Tools
        "get_supervisor_logs": "SYSTEM_TOOLS_GET_SUPERVISOR_LOGS",
        "get_homeassistant_logs": "SYSTEM_TOOLS_GET_HOMEASSISTANT_LOGS",
        "restart_homeassistant": "SYSTEM_TOOLS_RESTART_HOMEASSISTANT",
        "read_config_file": "SYSTEM_TOOLS_READ_CONFIG_FILE",
        "write_config_file": "SYSTEM_TOOLS_WRITE_CONFIG_FILE",
        "check_config": "SYSTEM_TOOLS_CHECK_CONFIG",
        # Backup Tools
        "create_backup": "BACKUP_TOOLS_CREATE_BACKUP",
        "list_backups": "BACKUP_TOOLS_LIST_BACKUPS",
        "get_backup_info": "BACKUP_TOOLS_GET_BACKUP_INFO",
        "restore_backup": "BACKUP_TOOLS_RESTORE_BACKUP",
        "delete_backup": "BACKUP_TOOLS_DELETE_BACKUP",
        # Integration Tools
        "list_integrations": "INTEGRATION_TOOLS_LIST_INTEGRATIONS",
        "reload_integration": "INTEGRATION_TOOLS_RELOAD_INTEGRATION",
        "get_integration_info": "INTEGRATION_TOOLS_GET_INTEGRATION_INFO",
        "remove_integration": "INTEGRATION_TOOLS_REMOVE_INTEGRATION",
        # Entity Tools
        "list_entities": "ENTITY_TOOLS_LIST_ENTITIES",
        "get_entity_state": "ENTITY_TOOLS_GET_ENTITY_STATE",
        "set_entity_state": "ENTITY_TOOLS_SET_ENTITY_STATE",
        "call_service": "ENTITY_TOOLS_CALL_SERVICE",
        "get_services": "ENTITY_TOOLS_GET_SERVICES",
        "get_entity_history": "ENTITY_TOOLS_GET_ENTITY_HISTORY",
        # Dashboard Tools
        "list_dashboards": "DASHBOARD_TOOLS_LIST_DASHBOARDS",
        "get_dashboard_config": "DASHBOARD_TOOLS_GET_DASHBOARD_CONFIG",
        "create_dashboard": "DASHBOARD_TOOLS_CREATE_DASHBOARD",
        "delete_dashboard": "DASHBOARD_TOOLS_DELETE_DASHBOARD",
        # Automation Tools
        "list_automations": "AUTOMATION_TOOLS_LIST_AUTOMATIONS",
        "get_automation": "AUTOMATION_TOOLS_GET_AUTOMATION",
        "create_automation": "AUTOMATION_TOOLS_CREATE_AUTOMATION",
        "update_automation": "AUTOMATION_TOOLS_UPDATE_AUTOMATION",
        "delete_automation": "AUTOMATION_TOOLS_DELETE_AUTOMATION",
        "enable_automation": "AUTOMATION_TOOLS_ENABLE_AUTOMATION",
        "disable_automation": "AUTOMATION_TOOLS_DISABLE_AUTOMATION",
        "trigger_automation": "AUTOMATION_TOOLS_TRIGGER_AUTOMATION",
        # Diagnostic Tools
        "get_system_health": "DIAGNOSTIC_TOOLS_GET_SYSTEM_HEALTH",
        "get_error_log_summary": "DIAGNOSTIC_TOOLS_GET_ERROR_LOG_SUMMARY",
        "list_unavailable_entities": "DIAGNOSTIC_TOOLS_LIST_UNAVAILABLE_ENTITIES",
        "get_recorder_stats": "DIAGNOSTIC_TOOLS_GET_RECORDER_STATS",
        "check_network_connectivity": "DIAGNOSTIC_TOOLS_CHECK_NETWORK_CONNECTIVITY",
        "list_custom_components": "DIAGNOSTIC_TOOLS_LIST_CUSTOM_COMPONENTS",
        "get_startup_time_breakdown": "DIAGNOSTIC_TOOLS_GET_STARTUP_TIME_BREAKDOWN",
        "validate_all_automations": "DIAGNOSTIC_TOOLS_VALIDATE_ALL_AUTOMATIONS",
        "list_deprecated_features": "DIAGNOSTIC_TOOLS_LIST_DEPRECATED_FEATURES",
        "get_integration_diagnostics": "DIAGNOSTIC_TOOLS_GET_INTEGRATION_DIAGNOSTICS",
    }
    
    # Build enabled tools list from environment variables
    # Default to true if not specified
    enabled_tools = []
    for tool_name, env_var in all_tools.items():
        # Get value from environment, default to "true"
        enabled = os.environ.get(env_var, "true").lower()
        # Convert to boolean
        # Enabled: true/1/yes
        # Disabled: false/0/no/off (anything else)
        if enabled in ("true", "1", "yes"):
            enabled_tools.append(tool_name)
        # Explicitly log disabled tools for debugging
        elif enabled in ("false", "0", "no", "off"):
            logger.debug(f"Tool disabled: {tool_name} (env: {env_var}={enabled})")
        else:
            # Unknown value, default to enabled for backwards compatibility
            logger.warning(f"Unknown value for {env_var}: {enabled}, defaulting to enabled")
            enabled_tools.append(tool_name)
    
    # Generate API key if not provided
    if not api_key:
        api_key = generate_api_key()
        logger.warning("=" * 80)
        logger.warning("NO API KEY CONFIGURED - Generated new API key:")
        logger.warning(f"API_KEY: {api_key}")
        logger.warning("Please save this key and add it to your add-on configuration!")
        logger.warning("=" * 80)
    
    logger.info("Configuration loaded:")
    logger.info(f"  HA Token configured: {bool(ha_token)}")
    logger.info(f"  API Key configured: {bool(api_key)}")
    logger.info(f"  Transport type: {transport_type}")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Enabled tools: {len(enabled_tools)}/{len(all_tools)} tools")
    if len(enabled_tools) < len(all_tools):
        disabled_tools = [tool for tool in all_tools.keys() if tool not in enabled_tools]
        logger.info(f"  Disabled tools: {', '.join(disabled_tools)}")
    
    return ServerConfig(
        ha_token=ha_token,
        api_key=api_key,
        transport_type=transport_type,
        host=host,
        port=port,
        enabled_tools=enabled_tools,
    )
