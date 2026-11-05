"""Read-only Home Assistant registry inventory API methods."""

from typing import Any

from .websocket_client import WebSocketClient


class InventoryAPI:
    """Mixin exposing area, device, and config-entry inventories."""

    async def _inventory_command(self, command_type: str, **kwargs) -> list[dict[str, Any]]:
        """Run a registry WebSocket command and normalize its list response."""
        if not self.ha_token:
            raise PermissionError("HA Core token is required for registry inventory tools")

        async with WebSocketClient(self.ha_url, self.ha_token) as websocket:
            result = await websocket.send_command(command_type, **kwargs)
        return result if isinstance(result, list) else []

    async def list_areas(self) -> list[dict[str, Any]]:
        """Return all entries in the Home Assistant area registry."""
        return await self._inventory_command("config/area_registry/list")

    async def list_devices(
        self, area_id: str | None = None, config_entry_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return devices, optionally filtered by area or config entry."""
        devices = await self._inventory_command("config/device_registry/list")
        if area_id:
            devices = [device for device in devices if device.get("area_id") == area_id]
        if config_entry_id:
            devices = [
                device
                for device in devices
                if config_entry_id
                in (device.get("config_entries") or [device.get("config_entry_id")])
            ]
        return devices

    async def list_config_entries(
        self, domain: str | None = None, state: str | None = None
    ) -> list[dict[str, Any]]:
        """Return config entries, optionally filtered by domain or state."""
        kwargs = {"domain": domain} if domain else {}
        entries = await self._inventory_command("config_entries/get", **kwargs)
        if state:
            entries = [entry for entry in entries if entry.get("state") == state]
        return entries
