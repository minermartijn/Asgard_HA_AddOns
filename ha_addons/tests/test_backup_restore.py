"""Regression tests for lifeboat single-add-on backup and restore."""

import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

src_dir = Path(__file__).parents[1] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from ha_client import HomeAssistantClient
from mcp_handlers import create_call_tool_handler, create_list_tools_handler
from tools.backup_tools import handle_backup_tool


class BackupClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = HomeAssistantClient(ha_token="mock")

    async def test_create_partial_backup_uses_exactly_one_addon(self):
        self.client._make_request = AsyncMock(return_value={"result": "ok", "job_id": "job-1", "data": {"slug": "backup-1"}})
        result = await self.client.create_addon_backup("local_ha_full_mcp", "Before update", "secret")
        self.assertEqual(result["slug"], "backup-1")
        self.client._make_request.assert_awaited_once_with(
            "POST", "http://supervisor/backups/new/partial", use_ha_token=False,
            json={"name": "Before update", "addons": ["local_ha_full_mcp"], "folders": [], "password": "secret"},
        )

    async def test_list_and_info_paths(self):
        self.client._make_request = AsyncMock(side_effect=[
            {"data": {"backups": [{"slug": "backup-1"}]}},
            {"data": {"slug": "backup-1", "content": {"addons": ["local_ha_full_mcp"]}}},
        ])
        self.assertEqual((await self.client.list_backups())[0]["slug"], "backup-1")
        self.assertEqual((await self.client.get_backup_info("backup-1"))["slug"], "backup-1")
        self.assertEqual(self.client._make_request.await_args_list[0].args[:2], ("GET", "http://supervisor/backups"))
        self.assertEqual(self.client._make_request.await_args_list[1].args[:2], ("GET", "http://supervisor/backups/backup-1/info"))

    async def test_restore_validates_membership_and_sends_single_addon(self):
        self.client._make_request = AsyncMock(side_effect=[
            {"data": {"slug": "backup-1", "protected": False, "content": {"addons": [{"slug": "local_ha_full_mcp"}]}}},
            {"result": "ok", "job_id": "job-2", "data": {}},
        ])
        result = await self.client.restore_addon_backup("backup-1", "local_ha_full_mcp")
        self.assertEqual(result["job_id"], "job-2")
        self.client._make_request.assert_awaited_with(
            "POST", "http://supervisor/backups/backup-1/restore/partial",
            use_ha_token=False, json={"addons": ["local_ha_full_mcp"], "folders": []},
        )

    async def test_restore_refuses_exclusion_mismatch(self):
        self.client._make_request = AsyncMock(return_value={"data": {"content": {"addons": ["core_ssh"]}}})
        with self.assertRaisesRegex(ValueError, "does not include addon"):
            await self.client.restore_addon_backup("backup-1", "local_ha_full_mcp")
        self.assertEqual(self.client._make_request.await_count, 1)

    async def test_encrypted_restore_requires_password(self):
        self.client._make_request = AsyncMock(return_value={"data": {"protected": True, "content": {"addons": ["local_ha_full_mcp"]}}})
        with self.assertRaisesRegex(ValueError, "password is required"):
            await self.client.restore_addon_backup("backup-1", "local_ha_full_mcp")

    async def test_api_errors_propagate(self):
        self.client._make_request = AsyncMock(side_effect=RuntimeError("Supervisor unavailable"))
        with self.assertRaisesRegex(RuntimeError, "Supervisor unavailable"):
            await self.client.list_backups()


class BackupToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_and_routing_include_four_backup_tools(self):
        client = AsyncMock()
        tools = await create_list_tools_handler(client)()
        names = {tool.name for tool in tools}
        self.assertTrue({"create_addon_backup", "list_backups", "get_backup_info", "restore_addon_backup"} <= names)
        client.list_backups.return_value = []
        response = await create_call_tool_handler(client)("list_backups", {})
        self.assertEqual(response[0].text, "No backups found.")

    async def test_missing_arguments_are_rejected(self):
        client = AsyncMock()
        response = await handle_backup_tool("restore_addon_backup", {"backup_slug": "backup-1"}, client)
        self.assertIn("required", response[0].text)
        client.restore_addon_backup.assert_not_awaited()

    async def test_password_is_redacted_from_call_log(self):
        client = AsyncMock()
        client.create_addon_backup.return_value = {"slug": "backup-1", "protected": True}
        handler = create_call_tool_handler(client)
        with self.assertLogs("mcp_handlers", level=logging.INFO) as captured:
            await handler("create_addon_backup", {"addon_slug": "full", "password": "top-secret"})
        logs = "\n".join(captured.output)
        self.assertIn("[REDACTED]", logs)
        self.assertNotIn("top-secret", logs)


if __name__ == "__main__":
    unittest.main()
