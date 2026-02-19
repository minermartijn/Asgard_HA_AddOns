"""Tool handlers for diagnostic tools."""
import logging
from typing import Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)


async def handle_diagnostic_tool(name: str, arguments: dict[str, Any], ha_client) -> list[TextContent]:
    """Handle diagnostic tool execution."""
    try:
        if name == "get_system_health":
            health = await ha_client.get_system_health()
            
            result = "# System Health Report\n\n"
            
            # Disk info
            disk = health.get("disk", {})
            result += "## 💾 Disk Usage\n\n"
            result += f"- **Total**: {disk.get('total_gb', 'N/A')} GB\n"
            result += f"- **Used**: {disk.get('used_gb', 'N/A')} GB ({disk.get('usage_percent', 'N/A')}%)\n"
            result += f"- **Free**: {disk.get('free_gb', 'N/A')} GB\n"
            if disk.get('lifetime_used_percent'):
                result += f"- **Disk Lifetime Used**: {disk.get('lifetime_used_percent')}%\n"
            result += "\n"
            
            # Database info
            db = health.get("database", {})
            result += "## 🗄️ Database\n\n"
            result += f"- **Size**: {db.get('size_mb', 'N/A')} MB\n\n"
            
            # System info
            system = health.get("system", {})
            result += "## 🖥️ System Information\n\n"
            result += f"- **Hostname**: {system.get('hostname', 'N/A')}\n"
            result += f"- **OS**: {system.get('operating_system', 'N/A')}\n"
            result += f"- **Kernel**: {system.get('kernel', 'N/A')}\n"
            result += f"- **Architecture**: {system.get('architecture', 'N/A')}\n"
            result += f"- **Startup Time**: {system.get('startup_time_seconds', 'N/A')} seconds\n"
            result += f"- **Timezone**: {system.get('timezone', 'N/A')}\n"
            result += f"- **NTP Synchronized**: {'✅' if system.get('dt_synchronized') else '❌'}\n\n"
            
            # Versions
            versions = health.get("versions", {})
            result += "## 📦 Versions\n\n"
            result += f"- **Supervisor**: {versions.get('supervisor', 'N/A')}\n"
            result += f"- **Core**: {versions.get('core', 'N/A')}\n"
            result += f"- **OS**: {versions.get('os', 'N/A')}\n\n"
            
            # Components
            components = health.get("components", {})
            result += "## 🔧 Components\n\n"
            result += f"- **Total Entities**: {components.get('total_entities', 0)}\n"
            result += f"- **Supervisor Healthy**: {'✅' if components.get('supervisor_healthy') else '❌'}\n"
            result += f"- **Supervisor Supported**: {'✅' if components.get('supervisor_supported') else '❌'}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_error_log_summary":
            lines = arguments.get("lines", 1000)
            summary = await ha_client.get_error_log_summary(lines)
            
            result = f"# Error Log Summary\n\n"
            result += f"**Analyzed**: {summary.get('lines_analyzed', 0)} log lines\n\n"
            
            # By severity
            by_severity = summary.get("by_severity", {})
            result += "## 📊 Errors by Severity\n\n"
            result += f"- **CRITICAL**: {by_severity.get('CRITICAL', 0)}\n"
            result += f"- **ERROR**: {by_severity.get('ERROR', 0)}\n"
            result += f"- **WARNING**: {by_severity.get('WARNING', 0)}\n"
            result += f"- **Total**: {summary.get('total_errors', 0)}\n\n"
            
            # By component
            by_component = summary.get("by_component", {})
            if by_component:
                result += "## 🔍 Top Error-Producing Components\n\n"
                for component, data in list(by_component.items())[:10]:
                    result += f"### {component} ({data.get('count', 0)} errors)\n\n"
                    for msg in data.get("messages", [])[:2]:
                        result += f"- **{msg.get('severity')}** [{msg.get('timestamp')}]: {msg.get('message')}\n"
                    result += "\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "list_unavailable_entities":
            unavailable = await ha_client.list_unavailable_entities()
            
            result = "# Unavailable Entities Report\n\n"
            result += f"**Total Unavailable**: {unavailable.get('total_unavailable', 0)} / {unavailable.get('total_entities', 0)} entities\n\n"
            
            by_domain = unavailable.get("by_domain", {})
            if by_domain:
                result += "## 📋 By Domain/Integration\n\n"
                for domain, entities in list(by_domain.items())[:15]:
                    result += f"### {domain} ({len(entities)} unavailable)\n\n"
                    for entity in entities[:5]:
                        result += f"- **{entity.get('entity_id')}** ({entity.get('state')})\n"
                        result += f"  - Name: {entity.get('friendly_name')}\n"
                        result += f"  - Last Changed: {entity.get('last_changed')}\n"
                    if len(entities) > 5:
                        result += f"  - ... and {len(entities) - 5} more\n"
                    result += "\n"
            else:
                result += "✅ **No unavailable entities found!**\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_recorder_stats":
            stats = await ha_client.get_recorder_stats()
            
            result = "# Database Statistics\n\n"
            result += f"**Path**: {stats.get('database_path', 'N/A')}\n\n"
            
            result += "## 📊 Size\n\n"
            result += f"- **Total**: {stats.get('total_size_mb', 'N/A')} MB ({stats.get('total_size_gb', 'N/A')} GB)\n\n"
            
            tables = stats.get("tables", {})
            if tables:
                result += "## 📑 Tables\n\n"
                sorted_tables = sorted(tables.items(), key=lambda x: x[1].get("row_count", 0), reverse=True)
                for table, data in sorted_tables[:15]:
                    result += f"- **{table}**: {data.get('row_count', 0):,} rows\n"
                result += "\n"
            
            date_range = stats.get("states_date_range", {})
            if date_range:
                result += "## 📅 States Date Range\n\n"
                result += f"- **Oldest**: {date_range.get('oldest', 'N/A')}\n"
                result += f"- **Newest**: {date_range.get('newest', 'N/A')}\n\n"
            
            if stats.get("detailed_stats_error"):
                result += f"⚠️ **Note**: {stats.get('detailed_stats_error')}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "check_network_connectivity":
            connectivity = await ha_client.check_network_connectivity()
            
            result = "# Network Connectivity Report\n\n"
            
            result += "## 🌐 Internet Connectivity\n\n"
            result += f"- **Host Internet**: {'✅ Connected' if connectivity.get('host_internet') else '❌ Disconnected'}\n"
            result += f"- **Supervisor Internet**: {'✅ Connected' if connectivity.get('supervisor_internet') else '❌ Disconnected'}\n\n"
            
            docker = connectivity.get("docker_network", {})
            if docker:
                result += "## 🐳 Docker Network\n\n"
                result += f"- **Interface**: {docker.get('interface', 'N/A')}\n"
                result += f"- **Address**: {docker.get('address', 'N/A')}\n"
                result += f"- **Gateway**: {docker.get('gateway', 'N/A')}\n"
                result += f"- **DNS**: {docker.get('dns', 'N/A')}\n\n"
            
            llmnr = connectivity.get("llmnr", {})
            mdns = connectivity.get("mdns", {})
            result += "## 📡 Network Services\n\n"
            result += f"- **LLMNR Hostname**: {llmnr.get('hostname', 'N/A')}\n"
            result += f"- **LLMNR Broadcast**: {'✅' if llmnr.get('broadcast') else '❌'}\n"
            result += f"- **mDNS Broadcast**: {'✅' if mdns.get('broadcast') else '❌'}\n\n"
            
            ntp = connectivity.get("ntp", {})
            result += "## ⏰ Time Synchronization\n\n"
            result += f"- **NTP Enabled**: {'✅' if ntp.get('enabled') else '❌'}\n"
            result += f"- **Synchronized**: {'✅' if ntp.get('synchronized') else '❌'}\n"
            
            return [TextContent(type="text", text=result)]

        elif name == "list_custom_components":
            custom = await ha_client.list_custom_components()
            
            result = "# Custom Components Report\n\n"
            
            if not custom.get("custom_components_found"):
                result += "ℹ️ **No custom_components directory found**\n"
                return [TextContent(type="text", text=result)]
            
            result += f"**Total Custom Components**: {custom.get('total_count', 0)}\n\n"
            
            components = custom.get("components", [])
            if components:
                result += "## 📦 Installed Custom Components\n\n"
                for comp in components:
                    result += f"### {comp.get('name', comp.get('domain'))}\n\n"
                    result += f"- **Domain**: {comp.get('domain')}\n"
                    if comp.get('version'):
                        result += f"- **Version**: {comp.get('version')}\n"
                    if comp.get('is_hacs'):
                        result += f"- **Source**: HACS\n"
                    if comp.get('documentation'):
                        result += f"- **Documentation**: {comp.get('documentation')}\n"
                    if comp.get('requirements'):
                        result += f"- **Requirements**: {', '.join(comp.get('requirements'))}\n"
                    if comp.get('manifest_error'):
                        result += f"- ⚠️ **Error**: {comp.get('manifest_error')}\n"
                    result += "\n"
            else:
                result += "✅ **No custom components installed**\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_startup_time_breakdown":
            startup = await ha_client.get_startup_time_breakdown()
            
            result = "# Startup Time Breakdown\n\n"
            result += f"**Total Setup Time**: {startup.get('total_setup_time', 0)} seconds\n"
            result += f"**Components Loaded**: {startup.get('component_count', 0)}\n"
            result += f"**Average Time**: {startup.get('average_time', 0)} seconds\n\n"
            
            bottlenecks = startup.get("bottlenecks", [])
            if bottlenecks:
                result += "## ⚠️ Bottlenecks (> 5 seconds)\n\n"
                for item in bottlenecks:
                    result += f"- **{item.get('component')}**: {item.get('time_seconds')} seconds\n"
                result += "\n"
            
            slowest = startup.get("slowest_components", [])
            if slowest:
                result += "## 🐌 Slowest Components\n\n"
                for item in slowest[:15]:
                    result += f"- **{item.get('component')}**: {item.get('time_seconds')} seconds\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "validate_all_automations":
            validation = await ha_client.validate_all_automations()
            
            if validation.get("error"):
                result = f"# Automation Validation\n\n"
                result += f"⚠️ **{validation.get('error')}**\n\n"
                result += f"💡 {validation.get('suggestion')}\n"
                return [TextContent(type="text", text=result)]
            
            result = "# Automation Validation Report\n\n"
            result += f"**Total Automations**: {validation.get('total_automations', 0)}\n"
            result += f"**With Issues**: {validation.get('automations_with_issues', 0)}\n"
            result += f"**Total Issues**: {validation.get('total_issues', 0)}\n\n"
            
            validations = validation.get("validations", [])
            if validations:
                result += "## ⚠️ Automations with Issues\n\n"
                for auto in validations:
                    result += f"### {auto.get('alias')} (ID: {auto.get('automation_id')})\n\n"
                    for issue in auto.get("issues", []):
                        result += f"- **{issue.get('type')}** in {issue.get('location')}: `{issue.get('entity_id')}`\n"
                    result += "\n"
            else:
                result += "✅ **All automations validated successfully!**\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "list_deprecated_features":
            deprecated = await ha_client.list_deprecated_features()
            
            result = "# Deprecated Features Report\n\n"
            result += f"**Deprecation Warnings Found**: {deprecated.get('deprecation_warnings_found', 0)}\n\n"
            
            warnings = deprecated.get("warnings", [])
            if warnings:
                result += "## ⚠️ Deprecation Warnings\n\n"
                for warning in warnings[:20]:
                    result += f"### {warning.get('component')}\n\n"
                    result += f"- **Time**: {warning.get('timestamp')}\n"
                    result += f"- **Message**: {warning.get('message')}\n\n"
            else:
                result += "✅ **No deprecation warnings found in logs**\n\n"
            
            result += f"## 💡 Recommendation\n\n{deprecated.get('recommendation')}\n\n"
            
            if deprecated.get('note'):
                result += f"ℹ️ **Note**: {deprecated.get('note')}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_integration_diagnostics":
            diagnostics = await ha_client.get_integration_diagnostics()
            
            result = "# Integration Diagnostics (by Domain)\n\n"
            result += f"**Total Domains**: {diagnostics.get('total_domains', 0)}\n"
            result += f"- ✅ **Healthy**: {diagnostics.get('healthy', 0)}\n"
            result += f"- ⚠️ **Degraded**: {diagnostics.get('degraded', 0)}\n"
            result += f"- ❌ **Error**: {diagnostics.get('error', 0)}\n\n"
            
            domains = diagnostics.get("domains", [])
            
            # Show errors first
            errors = [d for d in domains if d.get("health_status") == "error"]
            if errors:
                result += "## ❌ Domains with High Issue Rate (>25%)\n\n"
                for domain in errors:
                    result += f"### {domain.get('domain')}\n\n"
                    result += f"- **Total Entities**: {domain.get('entity_count', 0)}\n"
                    result += f"- **Unavailable**: {domain.get('unavailable_entities', 0)}\n"
                    result += f"- **Unknown**: {domain.get('unknown_entities', 0)}\n"
                    result += f"- **Issue Rate**: {domain.get('issue_percentage', 0)}%\n\n"
            
            # Show degraded
            degraded = [d for d in domains if d.get("health_status") == "degraded"]
            if degraded:
                result += "## ⚠️ Degraded Domains (<25% issues)\n\n"
                for domain in degraded[:10]:
                    result += f"### {domain.get('domain')}\n\n"
                    result += f"- **Total Entities**: {domain.get('entity_count', 0)}\n"
                    result += f"- **Issues**: {domain.get('total_issues', 0)} ({domain.get('issue_percentage', 0)}%)\n\n"
            
            if not errors and not degraded:
                result += "✅ **All domains are healthy!**\n\n"
            
            if diagnostics.get('note'):
                result += f"\nℹ️ **Note**: {diagnostics.get('note')}\n"
            
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown diagnostic tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing diagnostic tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]
