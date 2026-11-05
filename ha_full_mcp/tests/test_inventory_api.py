"""Regression tests for registry inventory API methods."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


aiohttp_stub = types.ModuleType("aiohttp")
aiohttp_stub.ClientSession = object
aiohttp_stub.ClientWebSocketResponse = object
aiohttp_stub.WSMsgType = types.SimpleNamespace(TEXT="text", ERROR="error")
sys.modules.setdefault("aiohttp", aiohttp_stub)

api_path = Path(__file__).parents[1] / "src" / "api"
sys.path.insert(0, str(api_path.parent))
module_path = api_path / "inventory_api.py"
spec = importlib.util.spec_from_file_location("api.inventory_api", module_path)
inventory_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory_api)
InventoryAPI = inventory_api.InventoryAPI


class InventoryClient(InventoryAPI):
    ha_url = "http://homeassistant:8123"
    ha_token = "test-token"


class InventoryAPITests(unittest.IsolatedAsyncioTestCase):
    async def test_registry_commands_and_filters(self):
        client = InventoryClient()
        client._inventory_command = AsyncMock(
            side_effect=[
                [{"area_id": "kitchen", "name": "Kitchen"}],
                [
                    {"id": "one", "area_id": "kitchen", "config_entries": ["hue"]},
                    {"id": "two", "area_id": "office", "config_entries": ["mqtt"]},
                ],
                [
                    {"entry_id": "hue", "domain": "hue", "state": "loaded"},
                    {"entry_id": "old", "domain": "hue", "state": "setup_error"},
                ],
            ]
        )

        self.assertEqual((await client.list_areas())[0]["area_id"], "kitchen")
        self.assertEqual(
            await client.list_devices(area_id="kitchen", config_entry_id="hue"),
            [{"id": "one", "area_id": "kitchen", "config_entries": ["hue"]}],
        )
        self.assertEqual(
            await client.list_config_entries(domain="hue", state="setup_error"),
            [{"entry_id": "old", "domain": "hue", "state": "setup_error"}],
        )
        self.assertEqual(
            client._inventory_command.await_args_list[0].args,
            ("config/area_registry/list",),
        )
        self.assertEqual(
            client._inventory_command.await_args_list[1].args,
            ("config/device_registry/list",),
        )
        self.assertEqual(
            client._inventory_command.await_args_list[2].kwargs,
            {"domain": "hue"},
        )

    async def test_requires_core_token(self):
        client = InventoryClient()
        client.ha_token = None
        with self.assertRaises(PermissionError):
            await client.list_areas()

    async def test_websocket_is_closed_after_command(self):
        client = InventoryClient()
        websocket = AsyncMock()
        websocket.send_command.return_value = [{"area_id": "office"}]
        context_manager = AsyncMock()
        context_manager.__aenter__.return_value = websocket

        with patch.object(inventory_api, "WebSocketClient", return_value=context_manager):
            result = await client.list_areas()

        self.assertEqual(result, [{"area_id": "office"}])
        context_manager.__aexit__.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
