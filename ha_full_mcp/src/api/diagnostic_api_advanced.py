"""Advanced diagnostic API methods - custom components, startup, automations, deprecations."""
import os
import re
import logging
from typing import Any
import aiohttp

logger = logging.getLogger(__name__)


class DiagnosticAdvancedAPI:
    """Mixin for advanced diagnostic API methods (custom components, startup, automations, deprecations, integrations)."""
    
    async def list_custom_components(self) -> dict[str, Any]:
        """List custom components and HACS integrations.
        
        Returns:
            Dictionary with custom component information
        
        Raises:
            IOError: If custom_components directory cannot be accessed
        """
        try:
            custom_dir = "/config/custom_components"
            
            if not os.path.exists(custom_dir):
                return {
                    "custom_components_found": False,
                    "total_count": 0,
                    "components": []
                }
            
            components = []
            
            for item in os.listdir(custom_dir):
                item_path = os.path.join(custom_dir, item)
                
                if os.path.isdir(item_path) and not item.startswith('.'):
                    component_info = {
                        "domain": item,
                        "path": item_path
                    }
                    
                    # Try to read manifest.json
                    manifest_path = os.path.join(item_path, "manifest.json")
                    if os.path.exists(manifest_path):
                        try:
                            import json
                            with open(manifest_path, 'r') as f:
                                manifest = json.load(f)
                                component_info["name"] = manifest.get("name", item)
                                component_info["version"] = manifest.get("version")
                                component_info["documentation"] = manifest.get("documentation")
                                component_info["issue_tracker"] = manifest.get("issue_tracker")
                                component_info["codeowners"] = manifest.get("codeowners", [])
                                component_info["requirements"] = manifest.get("requirements", [])
                                
                                # Check if it's a HACS component
                                if "hacs" in manifest.get("codeowners", []) or "hacs" in item.lower():
                                    component_info["is_hacs"] = True
                        except Exception as e:
                            logger.warning(f"Could not read manifest for {item}: {e}")
                            component_info["manifest_error"] = str(e)
                    
                    components.append(component_info)
            
            return {
                "custom_components_found": True,
                "total_count": len(components),
                "components": sorted(components, key=lambda x: x.get("domain", ""))
            }
            
        except Exception as e:
            logger.error(f"Failed to list custom components: {e}")
            raise IOError(f"Failed to access custom components: {str(e)}")
    
    async def get_startup_time_breakdown(self) -> dict[str, Any]:
        """Parse startup logs to show component load times.
        
        Returns:
            Dictionary with component load times and bottlenecks
        
        Raises:
            aiohttp.ClientError: If API request fails
        """
        try:
            # Get Home Assistant logs
            logs = await self.get_homeassistant_logs()
            
            # Parse for setup times
            component_times = {}
            setup_pattern = r'Setup of domain (\S+) took ([\d.]+) seconds'
            
            for line in logs.split('\n'):
                match = re.search(setup_pattern, line)
                if match:
                    component, time_str = match.groups()
                    try:
                        time_seconds = float(time_str)
                        component_times[component] = time_seconds
                    except ValueError:
                        continue
            
            # Sort by time (slowest first)
            sorted_times = sorted(
                component_times.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            total_time = sum(component_times.values())
            
            # Identify bottlenecks (> 5 seconds)
            bottlenecks = [
                {"component": comp, "time_seconds": time}
                for comp, time in sorted_times
                if time > 5.0
            ]
            
            return {
                "total_setup_time": round(total_time, 2),
                "component_count": len(component_times),
                "slowest_components": [
                    {"component": comp, "time_seconds": round(time, 2)}
                    for comp, time in sorted_times[:20]
                ],
                "bottlenecks": bottlenecks,
                "average_time": round(total_time / len(component_times), 2) if component_times else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get startup time breakdown: {e}")
            raise
    
    async def validate_all_automations(self) -> dict[str, Any]:
        """Validate all automations for syntax and entity references.
        
        Returns:
            Dictionary with validation results
        
        Raises:
            aiohttp.ClientError: If API request fails
        """
        try:
            # Get all automations
            automations_result = await self._make_request(
                "GET",
                f"{self.ha_url}/api/config/automation/config",
                use_ha_token=True
            )
            
            # Get all entity states to validate references
            states = await self._make_request(
                "GET",
                f"{self.ha_url}/api/states",
                use_ha_token=True
            )
            
            entity_ids = {entity.get("entity_id") for entity in states}
            
            validation_results = []
            total_issues = 0
            
            for automation in automations_result:
                automation_id = automation.get("id", "unknown")
                alias = automation.get("alias", "Unknown")
                
                issues = []
                
                # Check for entity references in triggers
                triggers = automation.get("trigger", [])
                for trigger in triggers:
                    entity_id = trigger.get("entity_id")
                    if entity_id and entity_id not in entity_ids:
                        issues.append({
                            "type": "missing_entity",
                            "location": "trigger",
                            "entity_id": entity_id
                        })
                
                # Check for entity references in conditions
                conditions = automation.get("condition", [])
                for condition in conditions:
                    entity_id = condition.get("entity_id")
                    if entity_id and entity_id not in entity_ids:
                        issues.append({
                            "type": "missing_entity",
                            "location": "condition",
                            "entity_id": entity_id
                        })
                
                # Check for entity references in actions
                actions = automation.get("action", [])
                for action in actions:
                    entity_id = action.get("entity_id")
                    target = action.get("target", {})
                    target_entity = target.get("entity_id") if isinstance(target, dict) else None
                    
                    if entity_id and entity_id not in entity_ids:
                        issues.append({
                            "type": "missing_entity",
                            "location": "action",
                            "entity_id": entity_id
                        })
                    elif target_entity and target_entity not in entity_ids:
                        issues.append({
                            "type": "missing_entity",
                            "location": "action_target",
                            "entity_id": target_entity
                        })
                
                if issues:
                    total_issues += len(issues)
                    validation_results.append({
                        "automation_id": automation_id,
                        "alias": alias,
                        "issues": issues
                    })
            
            return {
                "total_automations": len(automations_result),
                "automations_with_issues": len(validation_results),
                "total_issues": total_issues,
                "validations": validation_results
            }
            
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                # Automations might be in YAML file instead
                return {
                    "error": "Automations stored in YAML file, cannot validate via API",
                    "suggestion": "Use check_config tool to validate automations.yaml"
                }
            raise
        except Exception as e:
            logger.error(f"Failed to validate automations: {e}")
            raise
    
    async def list_deprecated_features(self) -> dict[str, Any]:
        """Scan for deprecated features and breaking changes.
        
        Returns:
            Dictionary with deprecated features found
        
        Raises:
            aiohttp.ClientError: If API request fails
        """
        try:
            # Get Home Assistant logs to find deprecation warnings
            logs = await self.get_homeassistant_logs()
            
            deprecation_warnings = []
            deprecation_pattern = r'(deprecated|deprecation|breaking change|will be removed)'
            
            for line in logs.split('\n'):
                if re.search(deprecation_pattern, line, re.IGNORECASE):
                    # Extract relevant info
                    match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(WARNING|ERROR)\s+\(([^)]+)\)\s+(.+)', line)
                    if match:
                        timestamp, severity, component, message = match.groups()
                        deprecation_warnings.append({
                            "timestamp": timestamp,
                            "component": component,
                            "message": message[:300]
                        })
            
            # Get supervisor logs for additional deprecation warnings
            try:
                supervisor_logs = await self.get_supervisor_logs()
                for line in supervisor_logs.split('\n'):
                    if re.search(deprecation_pattern, line, re.IGNORECASE):
                        # Add supervisor deprecation warnings
                        if "deprecated" in line.lower() or "deprecation" in line.lower():
                            deprecation_warnings.append({
                                "timestamp": "supervisor",
                                "component": "supervisor",
                                "message": line[:300]
                            })
            except Exception as e:
                logger.warning(f"Could not scan supervisor logs: {e}")
            
            return {
                "deprecation_warnings_found": len(deprecation_warnings),
                "warnings": deprecation_warnings[:50],  # Limit to 50
                "recommendation": "Review Home Assistant release notes for breaking changes",
                "note": "Scanned Home Assistant and Supervisor logs for deprecation warnings"
            }
            
        except Exception as e:
            logger.error(f"Failed to list deprecated features: {e}")
            raise
    
    async def get_integration_diagnostics(self) -> dict[str, Any]:
        """Get per-integration health and diagnostics.
        
        Returns:
            Dictionary with integration health information
        
        Raises:
            aiohttp.ClientError: If API request fails
        """
        try:
            # Get all entity states to analyze by domain
            states = await self._make_request(
                "GET",
                f"{self.ha_url}/api/states",
                use_ha_token=True
            )
            
            # Group entities by domain
            entities_by_domain = {}
            unavailable_by_domain = {}
            unknown_by_domain = {}
            
            for entity in states:
                entity_id = entity.get("entity_id", "")
                domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
                state = entity.get("state", "")
                
                entities_by_domain[domain] = entities_by_domain.get(domain, 0) + 1
                
                if state == "unavailable":
                    unavailable_by_domain[domain] = unavailable_by_domain.get(domain, 0) + 1
                elif state == "unknown":
                    unknown_by_domain[domain] = unknown_by_domain.get(domain, 0) + 1
            
            # Build integration diagnostics based on domains
            integration_health = []
            
            for domain in sorted(entities_by_domain.keys()):
                entity_count = entities_by_domain.get(domain, 0)
                unavailable_count = unavailable_by_domain.get(domain, 0)
                unknown_count = unknown_by_domain.get(domain, 0)
                
                # Calculate health status
                total_issues = unavailable_count + unknown_count
                issue_percentage = (total_issues / entity_count * 100) if entity_count > 0 else 0
                
                if issue_percentage == 0:
                    health_status = "healthy"
                elif issue_percentage < 25:
                    health_status = "degraded"
                else:
                    health_status = "error"
                
                integration_health.append({
                    "domain": domain,
                    "entity_count": entity_count,
                    "unavailable_entities": unavailable_count,
                    "unknown_entities": unknown_count,
                    "total_issues": total_issues,
                    "issue_percentage": round(issue_percentage, 1),
                    "health_status": health_status
                })
            
            # Sort by health status (errors first, then by issue count)
            integration_health.sort(key=lambda x: (
                0 if x["health_status"] == "error" else 1 if x["health_status"] == "degraded" else 2,
                -x["total_issues"]
            ))
            
            # Calculate summary
            healthy = sum(1 for i in integration_health if i["health_status"] == "healthy")
            degraded = sum(1 for i in integration_health if i["health_status"] == "degraded")
            error = sum(1 for i in integration_health if i["health_status"] == "error")
            
            return {
                "total_domains": len(integration_health),
                "healthy": healthy,
                "degraded": degraded,
                "error": error,
                "domains": integration_health,
                "note": "Analysis based on entity states by domain. Use list_unavailable_entities for detailed entity information."
            }
            
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get integration diagnostics: {e}")
            raise
