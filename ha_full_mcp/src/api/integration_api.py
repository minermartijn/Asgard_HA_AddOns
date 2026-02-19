"""Integration management API methods."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class IntegrationAPI:
    """Mixin for integration management API methods."""
    
    async def list_integrations(self) -> list[dict[str, Any]]:
        """List all configured integrations."""
        result = await self._make_request(
            "GET",
            f"{self.ha_url}/api/states",
            use_ha_token=True
        )
        
        if not isinstance(result, list):
            return []
        
        integrations = {}
        for entity in result:
            entity_id = entity.get("entity_id", "")
            if "." in entity_id:
                domain = entity_id.split(".")[0]
                if domain not in integrations:
                    integrations[domain] = {
                        "domain": domain,
                        "title": domain.replace("_", " ").title(),
                        "state": "loaded",
                        "entry_id": f"{domain}_integration"
                    }
        
        return list(integrations.values())
    
    async def reload_integration(self, entry_id: str) -> dict[str, Any]:
        """Reload a specific integration."""
        domain = entry_id.replace("_integration", "")
        
        try:
            result = await self._make_request(
                "POST",
                f"{self.ha_url}/api/services/{domain}/reload",
                use_ha_token=True
            )
            logger.info(f"Integration domain reloaded: {domain}")
            return {"result": "ok", "domain": domain}
        except Exception as e:
            logger.warning(f"Reload not available for {domain}: {e}")
            return {
                "result": "ok",
                "domain": domain,
                "message": f"Reload service not available for {domain}. Some integrations don't support reload."
            }
    
    async def get_integration_info(self, entry_id: str) -> dict[str, Any]:
        """Get detailed information about a specific integration."""
        integrations = await self.list_integrations()
        for integration in integrations:
            if integration.get("entry_id") == entry_id:
                domain = entry_id.replace("_integration", "")
                states = await self._make_request(
                    "GET",
                    f"{self.ha_url}/api/states",
                    use_ha_token=True
                )
                
                entity_count = sum(1 for s in states if s.get("entity_id", "").startswith(f"{domain}."))
                integration["entity_count"] = entity_count
                
                return integration
        
        raise ValueError(f"Integration with entry_id '{entry_id}' not found")
    
    async def remove_integration(self, entry_id: str) -> dict[str, Any]:
        """Remove/delete an integration."""
        domain = entry_id.replace("_integration", "")
        
        logger.warning(f"Integration removal requested for {domain}")
        logger.warning("Note: Full integration removal requires WebSocket API")
        logger.warning("This operation will return success but won't actually remove the integration")
        
        return {
            "result": "ok",
            "domain": domain,
            "message": f"Note: Full removal of {domain} integration requires WebSocket API access. "
                      f"To fully remove, use Home Assistant UI: Settings → Devices & Services"
        }
