"""System management API methods (logs, config files, restart)."""
import os
import logging
from typing import Any
import aiohttp

logger = logging.getLogger(__name__)


class SystemAPI:
    """Mixin for system management API methods."""
    
    async def get_supervisor_logs(self) -> str:
        """Get logs from the Home Assistant Supervisor."""
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

    async def get_homeassistant_logs(self) -> str:
        """Get logs from Home Assistant Core."""
        try:
            headers = self._get_headers(use_ha_token=False)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.hassio_url}/homeassistant/logs",
                    headers=headers
                ) as response:
                    if response.status == 403:
                        logger.error("Permission denied to access Home Assistant logs")
                        raise PermissionError("Insufficient permissions to access Home Assistant logs")
                    response.raise_for_status()
                    return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get Home Assistant logs: {e}")
            raise

    async def restart_homeassistant(self) -> dict[str, Any]:
        """Restart Home Assistant Core."""
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

    async def read_config_file(self, filename: str) -> str:
        """Read a Home Assistant configuration file."""
        if not filename or '..' in filename or '/' in filename or '\\' in filename:
            raise ValueError(f"Invalid filename: {filename}. Must be a simple filename without path separators.")
        
        allowed_extensions = ['.yaml', '.yml', '.json', '.txt', '.conf']
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            logger.warning(f"Reading file with uncommon extension: {filename}")
        
        try:
            file_path = f"/config/{filename}"
            logger.info(f"Reading config file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Successfully read {len(content)} bytes from {filename}")
            return content
            
        except FileNotFoundError:
            logger.error(f"Config file not found: {filename}")
            raise FileNotFoundError(f"File '{filename}' not found in /config directory")
        except PermissionError:
            logger.error(f"Permission denied reading config file: {filename}")
            raise PermissionError(f"Insufficient permissions to read '{filename}'")
        except Exception as e:
            logger.error(f"Failed to read config file {filename}: {e}")
            raise IOError(f"Failed to read file '{filename}': {str(e)}")

    async def write_config_file(self, filename: str, content: str, backup: bool = True) -> dict[str, Any]:
        """Write content to a Home Assistant configuration file."""
        if not filename or '..' in filename or '/' in filename or '\\' in filename:
            raise ValueError(f"Invalid filename: {filename}. Must be a simple filename without path separators.")
        
        if content is None:
            raise ValueError("Content cannot be None")
        
        try:
            file_path = f"/config/{filename}"
            backup_path = None
            
            logger.info(f"Writing config file: {file_path}")
            
            if backup and os.path.exists(file_path):
                import time
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_path = f"/config/.backup_{filename}.{timestamp}"
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as src:
                        backup_content = src.read()
                    with open(backup_path, 'w', encoding='utf-8') as dst:
                        dst.write(backup_content)
                    logger.info(f"Created backup: {backup_path}")
                except Exception as backup_error:
                    logger.warning(f"Failed to create backup: {backup_error}")
                    backup_path = None
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Successfully wrote {len(content)} bytes to {filename}")
            
            return {
                "result": "ok",
                "filename": filename,
                "path": file_path,
                "bytes_written": len(content),
                "backup_created": backup_path is not None,
                "backup_path": backup_path,
                "message": f"Successfully wrote to {filename}"
            }
            
        except PermissionError:
            logger.error(f"Permission denied writing config file: {filename}")
            raise PermissionError(f"Insufficient permissions to write '{filename}'")
        except Exception as e:
            logger.error(f"Failed to write config file {filename}: {e}")
            raise IOError(f"Failed to write file '{filename}': {str(e)}")

    async def check_config(self) -> dict[str, Any]:
        """Check/validate the Home Assistant configuration."""
        try:
            result = await self._make_request(
                "POST",
                f"{self.hassio_url}/core/api/config/core/check_config",
                use_ha_token=False
            )
            
            logger.info("Configuration check completed")
            
            errors = result.get("errors")
            is_valid = not errors or errors == ""
            
            return {
                "result": result.get("result", "ok"),
                "errors": errors,
                "valid": is_valid
            }
            
        except aiohttp.ClientResponseError as e:
            if e.status == 403:
                logger.error("Permission denied to check configuration")
                raise PermissionError("Insufficient permissions to check configuration") from e
            elif e.status == 401:
                logger.error("Unauthorized to check configuration - check API access")
                raise PermissionError("Unauthorized - check that supervisor_api and homeassistant_api are enabled") from e
            else:
                logger.error(f"Failed to check configuration: HTTP {e.status}")
                raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to check configuration: {e}")
            raise
