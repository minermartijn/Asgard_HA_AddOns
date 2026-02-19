"""Backup management API methods."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class BackupAPI:
    """Mixin for backup management API methods."""
    
    async def create_backup(self, name: str = None, password: str = None, 
                           addons: list[str] = None, folders: list[str] = None) -> dict[str, Any]:
        """Create a backup of Home Assistant."""
        payload = {}
        if name:
            payload["name"] = name
        if password:
            payload["password"] = password
        if addons is not None:
            payload["addons"] = addons
        if folders is not None:
            payload["folders"] = folders
        
        result = await self._make_request(
            "POST",
            f"{self.hassio_url}/backups/new/full" if not (addons or folders) else f"{self.hassio_url}/backups/new/partial",
            use_ha_token=False,
            json=payload if payload else None
        )
        
        logger.info(f"Backup created: {result.get('data', {}).get('slug')}")
        return {
            "slug": result.get("data", {}).get("slug"),
            "job_id": result.get("job_id"),
            **result.get("data", {})
        }
    
    async def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups."""
        result = await self._make_request("GET", f"{self.hassio_url}/backups", use_ha_token=False)
        return result.get("data", {}).get("backups", [])
    
    async def get_backup_info(self, slug: str) -> dict[str, Any]:
        """Get detailed information about a specific backup."""
        result = await self._make_request("GET", f"{self.hassio_url}/backups/{slug}/info", use_ha_token=False)
        return result.get("data", {})
    
    async def restore_backup(self, slug: str, password: str = None, 
                            addons: list[str] = None, folders: list[str] = None) -> dict[str, Any]:
        """Restore from a backup."""
        payload = {}
        if password:
            payload["password"] = password
        if addons is not None:
            payload["addons"] = addons
        if folders is not None:
            payload["folders"] = folders
        
        result = await self._make_request(
            "POST",
            f"{self.hassio_url}/backups/{slug}/restore/full" if not (addons or folders) else f"{self.hassio_url}/backups/{slug}/restore/partial",
            use_ha_token=False,
            json=payload if payload else None
        )
        
        logger.info(f"Backup restore initiated: {slug}")
        return {
            "result": result.get("result", "ok"),
            "job_id": result.get("job_id")
        }
    
    async def delete_backup(self, slug: str) -> dict[str, Any]:
        """Delete a backup."""
        result = await self._make_request(
            "DELETE",
            f"{self.hassio_url}/backups/{slug}",
            use_ha_token=False
        )
        
        logger.info(f"Backup deleted: {slug}")
        return {"result": result.get("result", "ok")}
