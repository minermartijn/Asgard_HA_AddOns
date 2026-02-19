"""Entity and service management API methods."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EntityAPI:
    """Mixin for entity and service management API methods."""
    
    async def list_entities(self, domain: str = None, area_id: str = None) -> list[dict[str, Any]]:
        """List all entities, optionally filtered by domain or area."""
        result = await self._make_request(
            "GET",
            f"{self.ha_url}/api/states",
            use_ha_token=True
        )
        
        entities = result if isinstance(result, list) else []
        
        if domain:
            entities = [e for e in entities if e.get('entity_id', '').startswith(f"{domain}.")]
        
        if area_id:
            logger.warning("Area filtering not fully implemented yet")
        
        return entities
    
    async def get_entity_state(self, entity_id: str) -> dict[str, Any]:
        """Get the current state of a specific entity."""
        result = await self._make_request(
            "GET",
            f"{self.ha_url}/api/states/{entity_id}",
            use_ha_token=True
        )
        return result
    
    async def set_entity_state(self, entity_id: str, state: str, 
                              attributes: dict[str, Any] = None) -> dict[str, Any]:
        """Set the state of an entity."""
        payload = {"state": state}
        if attributes:
            payload["attributes"] = attributes
        
        result = await self._make_request(
            "POST",
            f"{self.ha_url}/api/states/{entity_id}",
            use_ha_token=True,
            json=payload
        )
        
        logger.info(f"Entity state set: {entity_id} = {state}")
        return result
    
    async def call_service(self, domain: str, service: str, 
                          entity_id: str = None, data: dict[str, Any] = None) -> list[dict[str, Any]]:
        """Call a Home Assistant service."""
        payload = {}
        if entity_id:
            payload["entity_id"] = entity_id
        if data:
            payload.update(data)
        
        result = await self._make_request(
            "POST",
            f"{self.ha_url}/api/services/{domain}/{service}",
            use_ha_token=True,
            json=payload if payload else None
        )
        
        logger.info(f"Service called: {domain}.{service}")
        return result if isinstance(result, list) else []
    
    async def get_services(self) -> dict[str, Any]:
        """Get all available services."""
        result = await self._make_request(
            "GET",
            f"{self.ha_url}/api/services",
            use_ha_token=True
        )
        return result if isinstance(result, dict) else {}
    
    async def get_entity_history(self, entity_id: str, 
                                 start_time: str = None, end_time: str = None) -> list[list[dict[str, Any]]]:
        """Get historical state changes for an entity."""
        url = f"{self.ha_url}/api/history/period"
        if start_time:
            url += f"/{start_time}"
        
        url += f"?filter_entity_id={entity_id}"
        
        if end_time:
            url += f"&end_time={end_time}"
        
        result = await self._make_request(
            "GET",
            url,
            use_ha_token=True
        )
        
        return result if isinstance(result, list) else []
