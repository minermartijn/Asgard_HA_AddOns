"""Tool definitions for diagnostic tools."""
from mcp.types import Tool


def get_diagnostic_tool_definitions() -> list[Tool]:
    """Return all diagnostic-related tool definitions."""
    return [
        Tool(
            name="get_system_health",
            description="Get comprehensive system health information including CPU, memory, disk usage, database size, component count, and uptime. Essential for understanding overall system status and resource utilization.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_error_log_summary",
            description="Parse Home Assistant logs and summarize errors by component and severity. Shows the top error-producing components and recent error messages. Useful for identifying problematic integrations or recurring issues.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lines": {
                        "type": "integer",
                        "description": "Number of log lines to analyze (default: 1000). Higher values provide more historical context but take longer to process.",
                        "default": 1000
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="list_unavailable_entities",
            description="List all entities with 'unavailable' or 'unknown' state, grouped by integration/domain. Helps identify broken integrations, offline devices, or configuration issues. Shows when entities last changed state.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_recorder_stats",
            description="Get database and recorder statistics including database file size, table sizes, row counts, and date ranges. Essential for monitoring database growth and planning purge strategies. Helps identify database performance issues.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="check_network_connectivity",
            description="Check network connectivity status including DNS resolution, internet access, supervisor connectivity, and network interface status. Shows LLMNR/mDNS broadcast status and NTP synchronization. Useful for diagnosing network-related issues.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="list_custom_components",
            description="List all custom components and HACS integrations installed in /config/custom_components/. Shows component names, versions, documentation links, and requirements. Helps identify custom code that might cause issues or need updates.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_startup_time_breakdown",
            description="Parse startup logs to show component load times and identify bottlenecks. Shows which integrations take longest to initialize and total startup time. Useful for optimizing Home Assistant startup performance.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="validate_all_automations",
            description="Validate all automations for syntax errors and missing entity references. Checks triggers, conditions, and actions for entities that no longer exist. Helps prevent automation failures due to deleted or renamed entities.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="list_deprecated_features",
            description="Scan logs for deprecation warnings and breaking changes. Identifies features that will be removed in future Home Assistant versions. Helps plan upgrades and avoid breaking changes.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_integration_diagnostics",
            description="Get per-integration health status including entity counts, unavailable entities, and load state. Shows which integrations are healthy, degraded, or in error state. Useful for identifying problematic integrations at a glance.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]
