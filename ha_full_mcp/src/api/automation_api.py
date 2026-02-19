"""Automation management API methods using REST API."""
import logging
from typing import Any
import aiohttp

logger = logging.getLogger(__name__)


class AutomationAPI:
    """Mixin for automation management API methods."""
    
    async def list_automations(self) -> list[dict[str, Any]]:
        """List all automations using REST API.
        
        Returns:
            List of automation configurations
        """
        try:
            result = await self._make_request(
                "GET",
                f"{self.ha_url}/api/config/automation/config",
                use_ha_token=True
            )
            
            logger.info(f"Listed {len(result) if result else 0} automations")
            return result if isinstance(result, list) else []
        
        except Exception as e:
            logger.error(f"Failed to list automations: {e}")
            return []
    
    async def get_automation(self, automation_id: str) -> dict[str, Any]:
        """Get specific automation configuration.
        
        Args:
            automation_id: Automation ID
        
        Returns:
            Automation configuration
        """
        try:
            result = await self._make_request(
                "GET",
                f"{self.ha_url}/api/config/automation/config/{automation_id}",
                use_ha_token=True
            )
            
            logger.info(f"Retrieved automation: {automation_id}")
            return result if isinstance(result, dict) else {}
        
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.warning(f"Automation not found: {automation_id}")
                return {}
            raise
        except Exception as e:
            logger.error(f"Failed to get automation: {e}")
            return {}
    
    async def create_automation(self, automation_id: str, automation_config: dict[str, Any]) -> dict[str, Any]:
        """Create a new automation using REST API.
        
        Args:
            automation_id: Unique ID for the automation
            automation_config: Automation configuration with trigger, condition, action
        
        Returns:
            Created automation info
        """
        try:
            # Ensure ID is in config
            automation_config['id'] = automation_id
            
            result = await self._make_request(
                "POST",
                f"{self.ha_url}/api/config/automation/config/{automation_id}",
                use_ha_token=True,
                json=automation_config
            )
            
            logger.info(f"Created automation: {automation_config.get('alias', 'unnamed')}")
            return result if isinstance(result, dict) else automation_config
        
        except Exception as e:
            logger.error(f"Failed to create automation: {e}")
            raise
    
    async def update_automation(self, automation_id: str, automation_config: dict[str, Any]) -> dict[str, Any]:
        """Update an existing automation using REST API.
        
        Args:
            automation_id: Automation ID to update
            automation_config: New automation configuration
        
        Returns:
            Updated automation info
        """
        try:
            # Ensure ID is in config
            automation_config['id'] = automation_id
            
            result = await self._make_request(
                "POST",
                f"{self.ha_url}/api/config/automation/config/{automation_id}",
                use_ha_token=True,
                json=automation_config
            )
            
            logger.info(f"Updated automation: {automation_id}")
            return result if isinstance(result, dict) else automation_config
        
        except Exception as e:
            logger.error(f"Failed to update automation: {e}")
            raise
    
    async def delete_automation(self, automation_id: str) -> dict[str, Any]:
        """Delete an automation using REST API.
        
        Args:
            automation_id: Automation ID to delete
        
        Returns:
            Result of the operation
        """
        try:
            result = await self._make_request(
                "DELETE",
                f"{self.ha_url}/api/config/automation/config/{automation_id}",
                use_ha_token=True
            )
            
            logger.info(f"Deleted automation: {automation_id}")
            return result if isinstance(result, dict) else {"result": "ok"}
        
        except Exception as e:
            logger.error(f"Failed to delete automation: {e}")
            raise
    
    async def trigger_automation(self, entity_id: str, skip_condition: bool = True) -> list[dict[str, Any]]:
        """Trigger an automation manually.
        
        Args:
            entity_id: Automation entity ID (e.g., automation.my_automation)
            skip_condition: Skip condition checks (default: True)
        
        Returns:
            Service call result
        """
        try:
            # Use service call via REST API
            result = await self.call_service(
                domain='automation',
                service='trigger',
                entity_id=entity_id,
                data={'skip_condition': skip_condition}
            )
            
            logger.info(f"Triggered automation: {entity_id}")
            return result
        
        except Exception as e:
            logger.error(f"Failed to trigger automation: {e}")
            raise
    
    async def enable_automation(self, entity_id: str) -> list[dict[str, Any]]:
        """Enable an automation.
        
        Args:
            entity_id: Automation entity ID (e.g., automation.my_automation)
        
        Returns:
            Service call result
        """
        try:
            result = await self.call_service(
                domain='automation',
                service='turn_on',
                entity_id=entity_id
            )
            
            logger.info(f"Enabled automation: {entity_id}")
            return result
        
        except Exception as e:
            logger.error(f"Failed to enable automation: {e}")
            raise
    
    async def disable_automation(self, entity_id: str) -> list[dict[str, Any]]:
        """Disable an automation.
        
        Args:
            entity_id: Automation entity ID (e.g., automation.my_automation)
        
        Returns:
            Service call result
        """
        try:
            result = await self.call_service(
                domain='automation',
                service='turn_off',
                entity_id=entity_id
            )
            
            logger.info(f"Disabled automation: {entity_id}")
            return result
        
        except Exception as e:
            logger.error(f"Failed to disable automation: {e}")
            raise
