"""Base Home Assistant API Client with authentication and request handling."""
import os
import logging
from typing import Any
import aiohttp

logger = logging.getLogger(__name__)


class BaseClient:
    """Base client for Home Assistant API with authentication and request handling."""
    
    def __init__(self, ha_token: str = None):
        """Initialize the Home Assistant client.
        
        Args:
            ha_token: Long-lived access token for Home Assistant Core API (optional)
        """
        # Supervisor token for Supervisor API (addons, system)
        self.supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
        if not self.supervisor_token:
            logger.warning("SUPERVISOR_TOKEN not set - Supervisor API calls may fail")
        
        # Long-lived token for Home Assistant Core API (entities, services)
        self.ha_token = ha_token
        if not self.ha_token:
            logger.info("No HA token provided - Core API features will be limited")
        
        # Use the supervisor URLs
        self.ha_url = "http://homeassistant:8123"  # Direct to HA Core
        self.hassio_url = "http://supervisor"
        
        logger.info(f"HomeAssistantClient initialized:")
        logger.info(f"  - Supervisor token: {'SET' if self.supervisor_token else 'NOT SET'}")
        logger.info(f"  - HA Core token: {'SET' if self.ha_token else 'NOT SET'}")
    
    def _get_headers(self, use_ha_token: bool = False) -> dict[str, str]:
        """Get headers for API requests.
        
        Args:
            use_ha_token: If True, use HA Core token. Otherwise use Supervisor token.
        """
        token = self.ha_token if use_ha_token else self.supervisor_token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    
    async def _make_request(self, method: str, url: str, use_ha_token: bool = False, **kwargs) -> dict[str, Any]:
        """Make an HTTP request to Home Assistant API.
        
        Args:
            method: HTTP method
            url: Target URL
            use_ha_token: If True, use HA Core token instead of Supervisor token
        """
        headers = self._get_headers(use_ha_token)
        
        try:
            logger.debug(f"Making {method} request to {url}")
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, headers=headers, **kwargs
                ) as response:
                    logger.debug(f"Response status: {response.status}")
                    if response.status == 403:
                        text = await response.text()
                        logger.error(f"403 Forbidden: {text}")
                        token_type = "HA Core" if use_ha_token else "Supervisor"
                        raise PermissionError(f"{token_type} API access denied. Token set: {bool(headers.get('Authorization'))}")
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise
