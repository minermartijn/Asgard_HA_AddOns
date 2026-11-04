"""Regression tests for automation discovery."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock


aiohttp_stub = types.ModuleType("aiohttp")
aiohttp_stub.ClientResponseError = type("ClientResponseError", (Exception,), {})
sys.modules.setdefault("aiohttp", aiohttp_stub)

module_path = Path(__file__).parents[1] / "src" / "api" / "automation_api.py"
spec = importlib.util.spec_from_file_location("automation_api", module_path)
automation_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(automation_api)
AutomationAPI = automation_api.AutomationAPI


class AutomationClient(AutomationAPI):
    """Small test client exposing the automation mixin."""

    ha_url = "http://homeassistant:8123"


class ListAutomationsTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovers_states_and_enriches_config(self):
        client = AutomationClient()
        client._make_request = AsyncMock(
            side_effect=[
                [
                    {"entity_id": "light.kitchen", "state": "off"},
                    {
                        "entity_id": "automation.morning",
                        "state": "on",
                        "attributes": {
                            "id": "morning-123",
                            "friendly_name": "Morning routine",
                            "last_triggered": "2026-11-04T07:00:00+00:00",
                        },
                    },
                ],
                {
                    "id": "morning-123",
                    "alias": "Morning routine",
                    "trigger": [{"platform": "time", "at": "07:00:00"}],
                    "action": [{"service": "light.turn_on"}],
                },
            ]
        )

        result = await client.list_automations()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "morning-123")
        self.assertEqual(result[0]["entity_id"], "automation.morning")
        self.assertEqual(result[0]["state"], "on")
        self.assertEqual(len(result[0]["trigger"]), 1)
        client._make_request.assert_any_await(
            "GET", "http://homeassistant:8123/api/states", use_ha_token=True
        )
        client._make_request.assert_any_await(
            "GET",
            "http://homeassistant:8123/api/config/automation/config/morning-123",
            use_ha_token=True,
        )

    async def test_keeps_runtime_automation_without_config_id(self):
        client = AutomationClient()
        client._make_request = AsyncMock(
            return_value=[
                {
                    "entity_id": "automation.legacy",
                    "state": "off",
                    "attributes": {"friendly_name": "Legacy automation"},
                }
            ]
        )

        result = await client.list_automations()

        self.assertEqual(
            result,
            [
                {
                    "id": "automation.legacy",
                    "alias": "Legacy automation",
                    "entity_id": "automation.legacy",
                    "state": "off",
                    "last_triggered": None,
                }
            ],
        )
        client._make_request.assert_awaited_once()

    async def test_states_api_failure_is_not_reported_as_empty(self):
        client = AutomationClient()
        client._make_request = AsyncMock(side_effect=PermissionError("denied"))

        with self.assertRaises(PermissionError):
            await client.list_automations()


if __name__ == "__main__":
    unittest.main()
