"""Core diagnostic API methods - system health and errors."""
import os
import re
import logging
from typing import Any
import aiohttp

logger = logging.getLogger(__name__)


class DiagnosticCoreAPI:
    """Mixin for core diagnostic API methods (health, errors, entities, database, network)."""
    
    async def get_system_health(self) -> dict[str, Any]:
        """Get comprehensive system health information.
        
        Returns:
            Dictionary containing CPU, memory, disk, database size, component count, uptime
        
        Raises:
            aiohttp.ClientError: If API request fails
        """
        try:
            # Get host info for disk and system stats
            host_info = await self._make_request(
                "GET",
                f"{self.hassio_url}/host/info",
                use_ha_token=False
            )
            
            # Get supervisor info
            supervisor_info = await self._make_request(
                "GET",
                f"{self.hassio_url}/supervisor/info",
                use_ha_token=False
            )
            
            # Get core info
            core_info = await self._make_request(
                "GET",
                f"{self.hassio_url}/core/info",
                use_ha_token=False
            )
            
            # Get states to count entities
            states = await self._make_request(
                "GET",
                f"{self.ha_url}/api/states",
                use_ha_token=True
            )
            
            # Calculate database size if accessible
            db_size = None
            try:
                db_path = "/config/home-assistant_v2.db"
                if os.path.exists(db_path):
                    db_size = os.path.getsize(db_path)
            except Exception as e:
                logger.warning(f"Could not get database size: {e}")
            
            host_data = host_info.get("data", {})
            supervisor_data = supervisor_info.get("data", {})
            core_data = core_info.get("data", {})
            
            return {
                "disk": {
                    "total_gb": host_data.get("disk_total"),
                    "used_gb": host_data.get("disk_used"),
                    "free_gb": host_data.get("disk_free"),
                    "usage_percent": round((host_data.get("disk_used", 0) / host_data.get("disk_total", 1)) * 100, 2) if host_data.get("disk_total") else None,
                    "lifetime_used_percent": host_data.get("disk_life_time")
                },
                "database": {
                    "size_bytes": db_size,
                    "size_mb": round(db_size / 1024 / 1024, 2) if db_size else None
                },
                "system": {
                    "hostname": host_data.get("hostname"),
                    "operating_system": host_data.get("operating_system"),
                    "kernel": host_data.get("kernel"),
                    "architecture": supervisor_data.get("arch"),
                    "virtualization": host_data.get("virtualization"),
                    "chassis": host_data.get("chassis"),
                    "boot_timestamp": host_data.get("boot_timestamp"),
                    "startup_time_seconds": host_data.get("startup_time"),
                    "timezone": host_data.get("timezone"),
                    "dt_synchronized": host_data.get("dt_synchronized"),
                    "use_ntp": host_data.get("use_ntp")
                },
                "versions": {
                    "supervisor": supervisor_data.get("version"),
                    "core": core_data.get("version"),
                    "os": host_data.get("operating_system")
                },
                "components": {
                    "total_entities": len(states) if isinstance(states, list) else 0,
                    "supervisor_healthy": supervisor_data.get("healthy"),
                    "supervisor_supported": supervisor_data.get("supported")
                }
            }
            
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get system health: {e}")
            raise
    
    async def get_error_log_summary(self, lines: int = 1000) -> dict[str, Any]:
        """Parse logs and summarize errors by component.
        
        Args:
            lines: Number of log lines to analyze (default: 1000)
        
        Returns:
            Dictionary with error counts by component and severity
        
        Raises:
            aiohttp.ClientError: If API request fails
        """
        try:
            # Get Home Assistant logs
            logs = await self.get_homeassistant_logs()
            
            # Parse logs
            log_lines = logs.split('\n')[-lines:]
            
            errors_by_component = {}
            errors_by_severity = {"ERROR": 0, "WARNING": 0, "CRITICAL": 0}
            
            for line in log_lines:
                # Match log format: YYYY-MM-DD HH:MM:SS LEVEL (component) message
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(ERROR|WARNING|CRITICAL)\s+\(([^)]+)\)\s+(.+)', line)
                
                if match:
                    timestamp, severity, component, message = match.groups()
                    
                    # Count by severity
                    errors_by_severity[severity] = errors_by_severity.get(severity, 0) + 1
                    
                    # Count by component
                    if component not in errors_by_component:
                        errors_by_component[component] = {"count": 0, "messages": []}
                    
                    errors_by_component[component]["count"] += 1
                    
                    # Store first 3 messages per component
                    if len(errors_by_component[component]["messages"]) < 3:
                        errors_by_component[component]["messages"].append({
                            "timestamp": timestamp,
                            "severity": severity,
                            "message": message[:200]  # Truncate long messages
                        })
            
            # Sort components by error count
            sorted_components = sorted(
                errors_by_component.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )
            
            return {
                "total_errors": sum(errors_by_severity.values()),
                "by_severity": errors_by_severity,
                "by_component": dict(sorted_components[:20]),  # Top 20 components
                "lines_analyzed": len(log_lines)
            }
            
        except Exception as e:
            logger.error(f"Failed to parse error logs: {e}")
            raise
    
    async def list_unavailable_entities(self) -> dict[str, Any]:
        """List all unavailable or unknown entities grouped by integration.
        
        Returns:
            Dictionary with unavailable entities grouped by domain/integration
        
        Raises:
            aiohttp.ClientError: If API request fails
        """
        try:
            # Get all entity states
            states = await self._make_request(
                "GET",
                f"{self.ha_url}/api/states",
                use_ha_token=True
            )
            
            unavailable_entities = {}
            total_unavailable = 0
            
            for entity in states:
                entity_id = entity.get("entity_id", "")
                state = entity.get("state", "")
                
                # Check if entity is unavailable or unknown
                if state in ["unavailable", "unknown"]:
                    # Extract domain from entity_id
                    domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
                    
                    if domain not in unavailable_entities:
                        unavailable_entities[domain] = []
                    
                    unavailable_entities[domain].append({
                        "entity_id": entity_id,
                        "state": state,
                        "friendly_name": entity.get("attributes", {}).get("friendly_name", entity_id),
                        "last_changed": entity.get("last_changed"),
                        "last_updated": entity.get("last_updated")
                    })
                    
                    total_unavailable += 1
            
            # Sort domains by count
            sorted_domains = sorted(
                unavailable_entities.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
            
            return {
                "total_unavailable": total_unavailable,
                "total_entities": len(states),
                "by_domain": dict(sorted_domains)
            }
            
        except aiohttp.ClientError as e:
            logger.error(f"Failed to list unavailable entities: {e}")
            raise
    
    async def get_recorder_stats(self) -> dict[str, Any]:
        """Get database and recorder statistics.
        
        Returns:
            Dictionary with database size, table sizes, and purge status
        
        Raises:
            IOError: If database cannot be accessed
        """
        try:
            db_path = "/config/home-assistant_v2.db"
            
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Database not found at {db_path}")
            
            # Get database file size
            db_size = os.path.getsize(db_path)
            
            # Try to get more detailed stats using sqlite3
            stats = {
                "database_path": db_path,
                "total_size_bytes": db_size,
                "total_size_mb": round(db_size / 1024 / 1024, 2),
                "total_size_gb": round(db_size / 1024 / 1024 / 1024, 2)
            }
            
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get table sizes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                table_stats = {}
                for (table_name,) in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    table_stats[table_name] = {"row_count": count}
                
                stats["tables"] = table_stats
                
                # Get states table info (most important)
                if "states" in table_stats:
                    cursor.execute("SELECT MIN(last_updated), MAX(last_updated) FROM states")
                    min_date, max_date = cursor.fetchone()
                    stats["states_date_range"] = {
                        "oldest": min_date,
                        "newest": max_date
                    }
                
                conn.close()
                
            except Exception as e:
                logger.warning(f"Could not get detailed database stats: {e}")
                stats["detailed_stats_error"] = str(e)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get recorder stats: {e}")
            raise IOError(f"Failed to access database: {str(e)}")
    
    async def check_network_connectivity(self) -> dict[str, Any]:
        """Check network connectivity (DNS, internet, supervisor).
        
        Returns:
            Dictionary with connectivity test results
        
        Raises:
            aiohttp.ClientError: If API request fails
        """
        try:
            # Get network info from supervisor
            network_info = await self._make_request(
                "GET",
                f"{self.hassio_url}/network/info",
                use_ha_token=False
            )
            
            network_data = network_info.get("data", {})
            
            # Get host info for additional network details
            host_info = await self._make_request(
                "GET",
                f"{self.hassio_url}/host/info",
                use_ha_token=False
            )
            
            host_data = host_info.get("data", {})
            
            return {
                "host_internet": network_data.get("host_internet"),
                "supervisor_internet": network_data.get("supervisor_internet"),
                "docker_network": network_data.get("docker"),
                "interfaces": network_data.get("interfaces", []),
                "llmnr": {
                    "hostname": host_data.get("llmnr_hostname"),
                    "broadcast": host_data.get("broadcast_llmnr")
                },
                "mdns": {
                    "broadcast": host_data.get("broadcast_mdns")
                },
                "ntp": {
                    "synchronized": host_data.get("dt_synchronized"),
                    "enabled": host_data.get("use_ntp")
                }
            }
            
        except aiohttp.ClientError as e:
            logger.error(f"Failed to check network connectivity: {e}")
            raise
