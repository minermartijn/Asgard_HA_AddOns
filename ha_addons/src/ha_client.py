"""Home Assistant API Client for MCP Server."""
import os
import logging
from typing import Any
import aiohttp

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """Client for interacting with Home Assistant API."""
    
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
        self.ha_url = "http://supervisor/core"
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
    
    async def list_addons(self) -> list[dict[str, Any]]:
        """List all installed addons."""
        result = await self._make_request("GET", f"{self.hassio_url}/addons", use_ha_token=False)
        return result.get("data", {}).get("addons", [])
    
    async def get_addon_info(self, addon_slug: str) -> dict[str, Any]:
        """Get detailed information about a specific addon."""
        result = await self._make_request("GET", f"{self.hassio_url}/addons/{addon_slug}/info", use_ha_token=False)
        return result.get("data", {})
    
    async def start_addon(self, addon_slug: str) -> dict[str, Any]:
        """Start an addon."""
        result = await self._make_request("POST", f"{self.hassio_url}/addons/{addon_slug}/start", use_ha_token=False)
        return result.get("data", {})
    
    async def stop_addon(self, addon_slug: str) -> dict[str, Any]:
        """Stop an addon."""
        result = await self._make_request("POST", f"{self.hassio_url}/addons/{addon_slug}/stop", use_ha_token=False)
        return result.get("data", {})
    
    async def restart_addon(self, addon_slug: str) -> dict[str, Any]:
        """Restart an addon."""
        result = await self._make_request("POST", f"{self.hassio_url}/addons/{addon_slug}/restart", use_ha_token=False)
        return result.get("data", {})
    
    async def check_addon_update(self, addon_slug: str) -> dict[str, Any]:
        """Check if an addon has an available update.
        
        Returns addon info which includes version and version_latest.
        """
        info = await self.get_addon_info(addon_slug)
        return {
            "current_version": info.get("version"),
            "latest_version": info.get("version_latest"),
            "update_available": info.get("version") != info.get("version_latest"),
            "slug": info.get("slug"),
            "name": info.get("name"),
        }
    
    async def refresh_updates(self) -> dict[str, Any]:
        """Refresh the update cache to get the latest available updates."""
        result = await self._make_request("POST", f"{self.hassio_url}/refresh_updates", use_ha_token=False)
        return result.get("data", {})
    
    async def update_addon(self, addon_slug: str) -> dict[str, Any]:
        """Update an addon to the latest version."""
        result = await self._make_request("POST", f"{self.hassio_url}/addons/{addon_slug}/update", use_ha_token=False)
        return result.get("data", {})
    
    async def get_addon_logs(self, addon_slug: str) -> str:
        """Get logs from an addon."""
        try:
            headers = self._get_headers(use_ha_token=False)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.hassio_url}/addons/{addon_slug}/logs",
                    headers=headers
                ) as response:
                    response.raise_for_status()
                    return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get addon logs: {e}")
            raise
    
    async def install_addon(self, addon_slug: str, version: str = None) -> dict[str, Any]:
        """Install an addon from the store.
        
        Args:
            addon_slug: The slug of the addon to install
            version: Optional specific version to install (defaults to latest)
        
        Returns:
            Installation result data including job information for tracking progress
            
        Raises:
            ValueError: If addon_slug is invalid or addon not found in store
            PermissionError: If insufficient permissions to install addons
            aiohttp.ClientError: If API request fails
        """
        if not addon_slug:
            raise ValueError("addon_slug cannot be empty")
        
        json_data = {}
        if version:
            json_data["version"] = version
        
        try:
            result = await self._make_request(
                "POST", 
                f"{self.hassio_url}/addons/{addon_slug}/install",
                use_ha_token=False,
                json=json_data if json_data else None
            )
            
            # The API returns immediately with job information
            # The actual installation happens asynchronously
            data = result.get("data", {})
            
            # Log the installation initiation
            logger.info(f"Addon installation initiated for {addon_slug}")
            if "job_id" in result:
                logger.info(f"Installation job ID: {result['job_id']}")
            
            return {
                "result": result.get("result", "ok"),
                "job_id": result.get("job_id"),
                "addon_slug": addon_slug,
                "version": version,
                "data": data
            }
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.error(f"Addon {addon_slug} not found in store")
                raise ValueError(f"Addon '{addon_slug}' not found in store") from e
            elif e.status == 400:
                logger.error(f"Invalid request for addon {addon_slug}: {e}")
                raise ValueError(f"Invalid addon installation request: {e}") from e
            elif e.status == 403:
                logger.error(f"Permission denied to install addon {addon_slug}")
                raise PermissionError(f"Insufficient permissions to install addon '{addon_slug}'") from e
            else:
                logger.error(f"Failed to install addon {addon_slug}: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to install addon {addon_slug}: {e}")
            raise
    
    async def uninstall_addon(self, addon_slug: str) -> dict[str, Any]:
        """Uninstall an addon.
        
        Args:
            addon_slug: The slug of the addon to uninstall
        
        Returns:
            Uninstallation result data including job information for tracking progress
            
        Raises:
            ValueError: If addon_slug is invalid or addon not installed
            PermissionError: If insufficient permissions to uninstall addons
            aiohttp.ClientError: If API request fails
        """
        if not addon_slug:
            raise ValueError("addon_slug cannot be empty")
        
        try:
            result = await self._make_request(
                "POST", 
                f"{self.hassio_url}/addons/{addon_slug}/uninstall",
                use_ha_token=False
            )
            
            # The API returns immediately with job information
            # The actual uninstallation happens asynchronously
            data = result.get("data", {})
            
            # Log the uninstallation initiation
            logger.info(f"Addon uninstallation initiated for {addon_slug}")
            if "job_id" in result:
                logger.info(f"Uninstallation job ID: {result['job_id']}")
            
            return {
                "result": result.get("result", "ok"),
                "job_id": result.get("job_id"),
                "addon_slug": addon_slug,
                "data": data
            }
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.error(f"Addon {addon_slug} not found or not installed")
                raise ValueError(f"Addon '{addon_slug}' not found or not installed") from e
            elif e.status == 400:
                logger.error(f"Invalid request for addon {addon_slug}: {e}")
                raise ValueError(f"Invalid addon uninstallation request: {e}") from e
            elif e.status == 403:
                logger.error(f"Permission denied to uninstall addon {addon_slug}")
                raise PermissionError(f"Insufficient permissions to uninstall addon '{addon_slug}'") from e
            else:
                logger.error(f"Failed to uninstall addon {addon_slug}: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to uninstall addon {addon_slug}: {e}")
            raise
    
    async def get_addon_configuration(self, addon_slug: str) -> dict[str, Any]:
        """Get the configuration options for an addon.
        
        Args:
            addon_slug: The slug of the addon to get configuration for
        
        Returns:
            Dictionary containing the addon's configuration options and schema
            
        Raises:
            ValueError: If addon_slug is invalid or addon not found
            PermissionError: If insufficient permissions to access addon configuration
            aiohttp.ClientError: If API request fails
        """
        if not addon_slug:
            raise ValueError("addon_slug cannot be empty")
        
        try:
            # Get addon info which includes options
            info = await self.get_addon_info(addon_slug)
            
            # Extract configuration-related data
            options = info.get("options", {})
            schema = info.get("schema", {})
            
            return {
                "addon_slug": addon_slug,
                "addon_name": info.get("name", ""),
                "options": options,
                "schema": schema,
                "has_configuration": bool(schema)
            }
        except ValueError:
            # Re-raise ValueError from get_addon_info
            raise
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.error(f"Addon {addon_slug} not found")
                raise ValueError(f"Addon '{addon_slug}' not found") from e
            elif e.status == 403:
                logger.error(f"Permission denied to access addon {addon_slug} configuration")
                raise PermissionError(f"Insufficient permissions to access addon '{addon_slug}' configuration") from e
            else:
                logger.error(f"Failed to get addon {addon_slug} configuration: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get addon {addon_slug} configuration: {e}")
            raise
    
    async def set_addon_configuration(self, addon_slug: str, options: dict[str, Any], 
                                     boot: str = None, network: dict[str, Any] = None) -> dict[str, Any]:
        """Set the configuration options for an addon.
        
        Args:
            addon_slug: The slug of the addon to configure
            options: Dictionary of configuration options to set
            boot: Optional boot mode ('auto' or 'manual')
            network: Optional network configuration dictionary
        
        Returns:
            Dictionary containing the result of the configuration update
            
        Raises:
            ValueError: If addon_slug is invalid, addon not found, or configuration is invalid
            PermissionError: If insufficient permissions to modify addon configuration
            aiohttp.ClientError: If API request fails
        """
        if not addon_slug:
            raise ValueError("addon_slug cannot be empty")
        
        if not isinstance(options, dict):
            raise ValueError("options must be a dictionary")
        
        try:
            # Build the request payload
            payload = {"options": options}
            
            if boot is not None:
                if boot not in ["auto", "manual"]:
                    raise ValueError("boot must be 'auto' or 'manual'")
                payload["boot"] = boot
            
            if network is not None:
                if not isinstance(network, dict):
                    raise ValueError("network must be a dictionary")
                payload["network"] = network
            
            # Make the POST request to set options
            result = await self._make_request(
                "POST",
                f"{self.hassio_url}/addons/{addon_slug}/options",
                use_ha_token=False,
                json=payload
            )
            
            logger.info(f"Configuration updated for addon {addon_slug}")
            
            return {
                "result": result.get("result", "ok"),
                "addon_slug": addon_slug,
                "options_set": options,
                "boot": boot,
                "network": network
            }
            
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.error(f"Addon {addon_slug} not found")
                raise ValueError(f"Addon '{addon_slug}' not found") from e
            elif e.status == 400:
                # Configuration validation error
                error_text = await e.text() if hasattr(e, 'text') else str(e)
                logger.error(f"Invalid configuration for addon {addon_slug}: {error_text}")
                raise ValueError(f"Invalid configuration: {error_text}") from e
            elif e.status == 403:
                logger.error(f"Permission denied to configure addon {addon_slug}")
                raise PermissionError(f"Insufficient permissions to configure addon '{addon_slug}'") from e
            else:
                logger.error(f"Failed to set addon {addon_slug} configuration: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to set addon {addon_slug} configuration: {e}")
            raise
    
    async def validate_addon_configuration(self, addon_slug: str, options: dict[str, Any]) -> dict[str, Any]:
        """Validate configuration options for an addon without applying them.
        
        This method checks if the provided configuration options are valid according to
        the addon's schema without actually applying the changes. Useful for testing
        configuration before committing changes.
        
        Args:
            addon_slug: The slug of the addon to validate configuration for
            options: Dictionary of configuration options to validate
        
        Returns:
            Dictionary containing validation results with the following structure:
            {
                "valid": bool,  # True if configuration is valid
                "addon_slug": str,
                "options": dict,  # The options that were validated
                "errors": list,  # List of validation error messages (empty if valid)
                "message": str  # Human-readable validation result message
            }
            
        Raises:
            ValueError: If addon_slug is invalid or addon not found
            PermissionError: If insufficient permissions to validate addon configuration
            aiohttp.ClientError: If API request fails
        """
        if not addon_slug:
            raise ValueError("addon_slug cannot be empty")
        
        if not isinstance(options, dict):
            raise ValueError("options must be a dictionary")
        
        try:
            # Build the request payload
            payload = {"options": options}
            
            # Make the POST request to validate options
            # Note: The validate endpoint returns validation results
            result = await self._make_request(
                "POST",
                f"{self.hassio_url}/addons/{addon_slug}/options/validate",
                use_ha_token=False,
                json=payload
            )
            
            # If we get here, validation passed
            logger.info(f"Configuration validation passed for addon {addon_slug}")
            
            return {
                "valid": True,
                "addon_slug": addon_slug,
                "options": options,
                "errors": [],
                "message": "Configuration is valid",
                "result": result.get("result", "ok")
            }
            
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.error(f"Addon {addon_slug} not found")
                raise ValueError(f"Addon '{addon_slug}' not found") from e
            elif e.status == 400:
                # Validation failed - parse error details
                try:
                    error_data = await e.json() if hasattr(e, 'json') else {}
                    error_message = error_data.get("message", str(e))
                    
                    # Try to extract specific validation errors
                    errors = []
                    if isinstance(error_data, dict):
                        # Look for common error fields
                        if "message" in error_data:
                            errors.append(error_data["message"])
                        if "errors" in error_data and isinstance(error_data["errors"], list):
                            errors.extend(error_data["errors"])
                    
                    if not errors:
                        errors = [error_message]
                    
                    logger.info(f"Configuration validation failed for addon {addon_slug}: {errors}")
                    
                    return {
                        "valid": False,
                        "addon_slug": addon_slug,
                        "options": options,
                        "errors": errors,
                        "message": "Configuration validation failed",
                        "result": "error"
                    }
                except Exception:
                    # Fallback if we can't parse the error
                    error_text = str(e)
                    logger.info(f"Configuration validation failed for addon {addon_slug}: {error_text}")
                    
                    return {
                        "valid": False,
                        "addon_slug": addon_slug,
                        "options": options,
                        "errors": [error_text],
                        "message": "Configuration validation failed",
                        "result": "error"
                    }
            elif e.status == 403:
                logger.error(f"Permission denied to validate addon {addon_slug} configuration")
                raise PermissionError(f"Insufficient permissions to validate addon '{addon_slug}' configuration") from e
            else:
                logger.error(f"Failed to validate addon {addon_slug} configuration: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to validate addon {addon_slug} configuration: {e}")
            raise
    
    async def rebuild_addon(self, addon_slug: str) -> dict[str, Any]:
        """Rebuild an addon from source.
        
        This method rebuilds a local or custom addon from its source code.
        Useful for development or when addon source has been modified.
        Only works with local addons, not store addons.
        
        Args:
            addon_slug: The slug of the addon to rebuild
        
        Returns:
            Dictionary containing the result of the rebuild operation
            
        Raises:
            ValueError: If addon_slug is invalid, addon not found, or addon is not rebuildable
            PermissionError: If insufficient permissions to rebuild addon
            aiohttp.ClientError: If API request fails
        """
        if not addon_slug:
            raise ValueError("addon_slug cannot be empty")
        
        try:
            # Make the POST request to rebuild addon
            result = await self._make_request(
                "POST",
                f"{self.hassio_url}/addons/{addon_slug}/rebuild",
                use_ha_token=False
            )
            
            logger.info(f"Addon rebuild initiated for {addon_slug}")
            
            return {
                "result": result.get("result", "ok"),
                "addon_slug": addon_slug,
                "job_id": result.get("job_id"),
                "data": result.get("data", {})
            }
            
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.error(f"Addon {addon_slug} not found")
                raise ValueError(f"Addon '{addon_slug}' not found") from e
            elif e.status == 400:
                # Addon is not rebuildable (e.g., store addon)
                error_text = await e.text() if hasattr(e, 'text') else str(e)
                logger.error(f"Addon {addon_slug} cannot be rebuilt: {error_text}")
                raise ValueError(f"Addon '{addon_slug}' is not rebuildable. Only local/custom addons can be rebuilt.") from e
            elif e.status == 403:
                logger.error(f"Permission denied to rebuild addon {addon_slug}")
                raise PermissionError(f"Insufficient permissions to rebuild addon '{addon_slug}'") from e
            else:
                logger.error(f"Failed to rebuild addon {addon_slug}: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to rebuild addon {addon_slug}: {e}")
            raise

    async def list_store_addons(self, repository: str = None, search: str = None) -> list[dict[str, Any]]:
        """List all available addons from the Home Assistant add-on store.
        
        Args:
            repository: Optional repository filter (e.g., 'core', 'local')
            search: Optional search query to filter addons by name or description
        
        Returns:
            List of available store addons with their details
            
        Raises:
            PermissionError: If insufficient permissions to access store
            aiohttp.ClientError: If API request fails
        """
        try:
            # Get store information which includes available addons
            result = await self._make_request("GET", f"{self.hassio_url}/store", use_ha_token=False)
            store_data = result.get("data", {})
            
            # Get list of addons from store
            addons = store_data.get("addons", [])
            
            # Apply repository filter if provided
            if repository:
                addons = [addon for addon in addons if addon.get("repository") == repository]
            
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                addons = [
                    addon for addon in addons
                    if search_lower in addon.get("name", "").lower() 
                    or search_lower in addon.get("description", "").lower()
                    or search_lower in addon.get("slug", "").lower()
                ]
            
            logger.info(f"Retrieved {len(addons)} store addons")
            return addons
            
        except aiohttp.ClientResponseError as e:
            if e.status == 403:
                logger.error("Permission denied to access addon store")
                raise PermissionError("Insufficient permissions to access addon store") from e
            else:
                logger.error(f"Failed to list store addons: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to list store addons: {e}")
            raise
    
    async def reload_addons(self) -> dict[str, Any]:
        """Reload the addon list to refresh available addons.
        
        This is useful after adding a new repository or when the addon list
        needs to be refreshed without restarting Home Assistant.
        
        Returns:
            Dictionary containing the result of the reload operation
            
        Raises:
            PermissionError: If insufficient permissions to reload addons
            aiohttp.ClientError: If API request fails
        """
        try:
            result = await self._make_request(
                "POST",
                f"{self.hassio_url}/addons/reload",
                use_ha_token=False
            )
            
            logger.info("Addon list reloaded successfully")
            
            return {
                "result": result.get("result", "ok"),
                "message": "Addon list reloaded successfully"
            }
            
        except aiohttp.ClientResponseError as e:
            if e.status == 403:
                logger.error("Permission denied to reload addons")
                raise PermissionError("Insufficient permissions to reload addons") from e
            else:
                logger.error(f"Failed to reload addons: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to reload addons: {e}")
            raise
    
    async def check_addon_availability(self, addon_slug: str) -> dict[str, Any]:
        """Check if an addon is available for installation on this system.
        
        This checks architecture compatibility, dependencies, and other
        requirements to determine if an addon can be installed.
        
        Args:
            addon_slug: The slug of the addon to check
        
        Returns:
            Dictionary containing availability information:
            {
                "available": bool,
                "addon_slug": str,
                "addon_name": str,
                "reason": str,  # Explanation if unavailable
                "architecture": str,  # System architecture
                "compatible": bool  # Architecture compatibility
            }
            
        Raises:
            ValueError: If addon_slug is invalid or addon not found
            PermissionError: If insufficient permissions
            aiohttp.ClientError: If API request fails
        """
        if not addon_slug:
            raise ValueError("addon_slug cannot be empty")
        
        try:
            # Get addon info from store
            result = await self._make_request(
                "GET",
                f"{self.hassio_url}/store/addons/{addon_slug}",
                use_ha_token=False
            )
            
            addon_data = result.get("data", {})
            
            # Check if addon is available
            available = addon_data.get("available", False)
            arch_list = addon_data.get("arch", [])
            
            # Get system architecture
            supervisor_info = await self._make_request(
                "GET",
                f"{self.hassio_url}/supervisor/info",
                use_ha_token=False
            )
            system_arch = supervisor_info.get("data", {}).get("arch", "unknown")
            
            # Check architecture compatibility
            compatible = system_arch in arch_list if arch_list else False
            
            # Determine reason if unavailable
            reason = ""
            if not available:
                if not compatible:
                    reason = f"Addon not compatible with system architecture ({system_arch}). Supported: {', '.join(arch_list)}"
                else:
                    reason = addon_data.get("available_reason", "Addon is not available for installation")
            
            logger.info(f"Addon {addon_slug} availability checked: {available}")
            
            return {
                "available": available,
                "addon_slug": addon_slug,
                "addon_name": addon_data.get("name", addon_slug),
                "reason": reason,
                "architecture": system_arch,
                "compatible": compatible,
                "supported_architectures": arch_list
            }
            
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.error(f"Addon {addon_slug} not found in store")
                raise ValueError(f"Addon '{addon_slug}' not found in store") from e
            elif e.status == 403:
                logger.error(f"Permission denied to check addon {addon_slug} availability")
                raise PermissionError(f"Insufficient permissions to check addon availability") from e
            else:
                logger.error(f"Failed to check addon {addon_slug} availability: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to check addon {addon_slug} availability: {e}")
            raise

    async def get_supervisor_logs(self) -> str:
        """Get logs from the Home Assistant Supervisor.
        
        This is useful for debugging addon builds, supervisor issues,
        and system-level problems.
        
        Returns:
            String containing the supervisor logs
            
        Raises:
            PermissionError: If insufficient permissions to access supervisor logs
            aiohttp.ClientError: If API request fails
        """
        try:
            headers = self._get_headers(use_ha_token=False)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.hassio_url}/supervisor/logs",
                    headers=headers
                ) as response:
                    if response.status == 403:
                        logger.error("Permission denied to access supervisor logs")
                        raise PermissionError("Insufficient permissions to access supervisor logs")
                    response.raise_for_status()
                    return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get supervisor logs: {e}")
            raise

    async def restart_homeassistant(self) -> dict[str, Any]:
        """Restart Home Assistant Core.
        
        This restarts the Home Assistant Core service. The Supervisor and addons
        will continue running. Use this after configuration changes that require
        a restart.
        
        Returns:
            Dictionary containing the result of the restart operation
            
        Raises:
            PermissionError: If insufficient permissions to restart Home Assistant
            aiohttp.ClientError: If API request fails
        """
        try:
            result = await self._make_request(
                "POST",
                f"{self.hassio_url}/homeassistant/restart",
                use_ha_token=False
            )
            
            logger.info("Home Assistant restart initiated")
            
            return {
                "result": result.get("result", "ok"),
                "message": "Home Assistant restart initiated"
            }
            
        except aiohttp.ClientResponseError as e:
            if e.status == 403:
                logger.error("Permission denied to restart Home Assistant")
                raise PermissionError("Insufficient permissions to restart Home Assistant") from e
            else:
                logger.error(f"Failed to restart Home Assistant: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to restart Home Assistant: {e}")
            raise
