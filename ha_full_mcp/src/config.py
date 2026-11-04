"""
Configuration management for Home Assistant MCP Server.
"""

import os
import json
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
    server_version: str = "1.10.3"


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


def load_config() -> ServerConfig:
    """Load configuration from /data/options.json (Home Assistant) with env fallback."""
    # Read Home Assistant options.json if present
    options_data: dict = {}
    options_file = os.environ.get("OPTIONS_PATH", "/data/options.json")
    if os.path.exists(options_file):
        try:
            with open(options_file, "r", encoding="utf-8") as f:
                options_data = json.load(f)
            logger.info(f"Loaded add-on configuration from {options_file}")
        except Exception as e:
            logger.warning(f"Could not read {options_file}: {e}")

    # Base options (options.json takes precedence, falls back to env vars)
    ha_token = options_data.get("ha_token") or os.environ.get("HA_TOKEN")
    api_key = str(options_data.get("api_key") or os.environ.get("API_KEY", "")).strip()

    raw_transport = str(options_data.get("transport") or os.environ.get("TRANSPORT", "sse")).lower().strip()
    if raw_transport in ("streamable-http", "streamable_http", "streamablehttp"):
        transport_type = "streamable-http"
    elif raw_transport == "stdio":
        transport_type = "stdio"
    elif raw_transport in ("all", "both"):
        transport_type = "all"
    else:
        transport_type = "sse"

    host = str(options_data.get("host") or os.environ.get("HOST", "0.0.0.0"))
    try:
        port = int(options_data.get("port") or os.environ.get("PORT", "8010"))
    except (ValueError, TypeError):
        port = 8010

    # Define all available tools mapped to (section, subkey, fallback_env_var)
    all_tools = {
        # Addon Information Tools
        "list_addons": ("addon_information", "list_addons", "ADDON_INFORMATION_LIST_ADDONS"),
        "get_addon_info": ("addon_information", "get_addon_info", "ADDON_INFORMATION_GET_ADDON_INFO"),
        "get_addon_logs": ("addon_information", "get_addon_logs", "ADDON_INFORMATION_GET_ADDON_LOGS"),
        # Addon Control Tools
        "start_addon": ("addon_control", "start_addon", "ADDON_CONTROL_START_ADDON"),
        "stop_addon": ("addon_control", "stop_addon", "ADDON_CONTROL_STOP_ADDON"),
        "restart_addon": ("addon_control", "restart_addon", "ADDON_CONTROL_RESTART_ADDON"),
        # Addon Management Tools
        "update_addon": ("addon_management", "update_addon", "ADDON_MANAGEMENT_UPDATE_ADDON"),
        "install_addon": ("addon_management", "install_addon", "ADDON_MANAGEMENT_INSTALL_ADDON"),
        "uninstall_addon": ("addon_management", "uninstall_addon", "ADDON_MANAGEMENT_UNINSTALL_ADDON"),
        # Addon Configuration Tools
        "get_addon_configuration": ("addon_configuration", "get_addon_configuration", "ADDON_CONFIGURATION_GET_ADDON_CONFIGURATION"),
        "set_addon_configuration": ("addon_configuration", "set_addon_configuration", "ADDON_CONFIGURATION_SET_ADDON_CONFIGURATION"),
        "validate_addon_configuration": ("addon_configuration", "validate_addon_configuration", "ADDON_CONFIGURATION_VALIDATE_ADDON_CONFIGURATION"),
        # Addon Advanced Tools
        "rebuild_addon": ("addon_advanced", "rebuild_addon", "ADDON_ADVANCED_REBUILD_ADDON"),
        "list_store_addons": ("addon_advanced", "list_store_addons", "ADDON_ADVANCED_LIST_STORE_ADDONS"),
        "reload_addons": ("addon_advanced", "reload_addons", "ADDON_ADVANCED_RELOAD_ADDONS"),
        "check_addon_availability": ("addon_advanced", "check_addon_availability", "ADDON_ADVANCED_CHECK_ADDON_AVAILABILITY"),
        # System Tools
        "get_supervisor_logs": ("system_tools", "get_supervisor_logs", "SYSTEM_TOOLS_GET_SUPERVISOR_LOGS"),
        "get_homeassistant_logs": ("system_tools", "get_homeassistant_logs", "SYSTEM_TOOLS_GET_HOMEASSISTANT_LOGS"),
        "restart_homeassistant": ("system_tools", "restart_homeassistant", "SYSTEM_TOOLS_RESTART_HOMEASSISTANT"),
        "read_config_file": ("system_tools", "read_config_file", "SYSTEM_TOOLS_READ_CONFIG_FILE"),
        "write_config_file": ("system_tools", "write_config_file", "SYSTEM_TOOLS_WRITE_CONFIG_FILE"),
        "check_config": ("system_tools", "check_config", "SYSTEM_TOOLS_CHECK_CONFIG"),
        # Backup Tools
        "create_backup": ("backup_tools", "create_backup", "BACKUP_TOOLS_CREATE_BACKUP"),
        "list_backups": ("backup_tools", "list_backups", "BACKUP_TOOLS_LIST_BACKUPS"),
        "get_backup_info": ("backup_tools", "get_backup_info", "BACKUP_TOOLS_GET_BACKUP_INFO"),
        "restore_backup": ("backup_tools", "restore_backup", "BACKUP_TOOLS_RESTORE_BACKUP"),
        "delete_backup": ("backup_tools", "delete_backup", "BACKUP_TOOLS_DELETE_BACKUP"),
        # Integration Tools
        "list_integrations": ("integration_tools", "list_integrations", "INTEGRATION_TOOLS_LIST_INTEGRATIONS"),
        "reload_integration": ("integration_tools", "reload_integration", "INTEGRATION_TOOLS_RELOAD_INTEGRATION"),
        "get_integration_info": ("integration_tools", "get_integration_info", "INTEGRATION_TOOLS_GET_INTEGRATION_INFO"),
        "remove_integration": ("integration_tools", "remove_integration", "INTEGRATION_TOOLS_REMOVE_INTEGRATION"),
        # Entity Tools
        "list_entities": ("entity_tools", "list_entities", "ENTITY_TOOLS_LIST_ENTITIES"),
        "get_entity_state": ("entity_tools", "get_entity_state", "ENTITY_TOOLS_GET_ENTITY_STATE"),
        "set_entity_state": ("entity_tools", "set_entity_state", "ENTITY_TOOLS_SET_ENTITY_STATE"),
        "call_service": ("entity_tools", "call_service", "ENTITY_TOOLS_CALL_SERVICE"),
        "get_services": ("entity_tools", "get_services", "ENTITY_TOOLS_GET_SERVICES"),
        "get_entity_history": ("entity_tools", "get_entity_history", "ENTITY_TOOLS_GET_ENTITY_HISTORY"),
        # Dashboard Tools
        "list_dashboards": ("dashboard_tools", "list_dashboards", "DASHBOARD_TOOLS_LIST_DASHBOARDS"),
        "get_dashboard_config": ("dashboard_tools", "get_dashboard_config", "DASHBOARD_TOOLS_GET_DASHBOARD_CONFIG"),
        "create_dashboard": ("dashboard_tools", "create_dashboard", "DASHBOARD_TOOLS_CREATE_DASHBOARD"),
        "delete_dashboard": ("dashboard_tools", "delete_dashboard", "DASHBOARD_TOOLS_DELETE_DASHBOARD"),
        # Automation Tools
        "list_automations": ("automation_tools", "list_automations", "AUTOMATION_TOOLS_LIST_AUTOMATIONS"),
        "get_automation": ("automation_tools", "get_automation", "AUTOMATION_TOOLS_GET_AUTOMATION"),
        "create_automation": ("automation_tools", "create_automation", "AUTOMATION_TOOLS_CREATE_AUTOMATION"),
        "update_automation": ("automation_tools", "update_automation", "AUTOMATION_TOOLS_UPDATE_AUTOMATION"),
        "delete_automation": ("automation_tools", "delete_automation", "AUTOMATION_TOOLS_DELETE_AUTOMATION"),
        "enable_automation": ("automation_tools", "enable_automation", "AUTOMATION_TOOLS_ENABLE_AUTOMATION"),
        "disable_automation": ("automation_tools", "disable_automation", "AUTOMATION_TOOLS_DISABLE_AUTOMATION"),
        "trigger_automation": ("automation_tools", "trigger_automation", "AUTOMATION_TOOLS_TRIGGER_AUTOMATION"),
        # Diagnostic Tools
        "get_system_health": ("diagnostic_tools", "get_system_health", "DIAGNOSTIC_TOOLS_GET_SYSTEM_HEALTH"),
        "get_error_log_summary": ("diagnostic_tools", "get_error_log_summary", "DIAGNOSTIC_TOOLS_GET_ERROR_LOG_SUMMARY"),
        "list_unavailable_entities": ("diagnostic_tools", "list_unavailable_entities", "DIAGNOSTIC_TOOLS_LIST_UNAVAILABLE_ENTITIES"),
        "get_recorder_stats": ("diagnostic_tools", "get_recorder_stats", "DIAGNOSTIC_TOOLS_GET_RECORDER_STATS"),
        "check_network_connectivity": ("diagnostic_tools", "check_network_connectivity", "DIAGNOSTIC_TOOLS_CHECK_NETWORK_CONNECTIVITY"),
        "list_custom_components": ("diagnostic_tools", "list_custom_components", "DIAGNOSTIC_TOOLS_LIST_CUSTOM_COMPONENTS"),
        "get_startup_time_breakdown": ("diagnostic_tools", "get_startup_time_breakdown", "DIAGNOSTIC_TOOLS_GET_STARTUP_TIME_BREAKDOWN"),
        "validate_all_automations": ("diagnostic_tools", "validate_all_automations", "DIAGNOSTIC_TOOLS_VALIDATE_ALL_AUTOMATIONS"),
        "list_deprecated_features": ("diagnostic_tools", "list_deprecated_features", "DIAGNOSTIC_TOOLS_LIST_DEPRECATED_FEATURES"),
        "get_integration_diagnostics": ("diagnostic_tools", "get_integration_diagnostics", "DIAGNOSTIC_TOOLS_GET_INTEGRATION_DIAGNOSTICS"),
    }

    # Build enabled tools list: options.json section first, then env var
    enabled_tools = []
    for tool_name, (section, subkey, env_var) in all_tools.items():
        if (
            section in options_data
            and isinstance(options_data[section], dict)
            and subkey in options_data[section]
        ):
            val = options_data[section][subkey]
            is_enabled = bool(val)
        else:
            env_val = os.environ.get(env_var, "true").lower()
            is_enabled = env_val in ("true", "1", "yes")

        if is_enabled:
            enabled_tools.append(tool_name)
        else:
            logger.debug(f"Tool disabled: {tool_name}")

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
