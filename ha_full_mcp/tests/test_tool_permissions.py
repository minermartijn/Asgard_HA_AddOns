"""Security regressions for Full MCP tool toggles and logging."""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

src = Path(__file__).parents[1] / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

import mcp_handlers  # noqa: E402
from mcp.types import TextContent  # noqa: E402


class ToolPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_tool_is_not_executed(self):
        """A hidden/disabled tool must not be callable by name."""
        client = object()
        callback = mcp_handlers.create_call_tool_handler(
            client, enabled_tools=["list_addons"]
        )
        with patch.object(
            mcp_handlers, "handle_addon_tool", new_callable=AsyncMock
        ) as handler:
            response = await callback("uninstall_addon", {"addon_slug": "dummy"})
            handler.assert_not_awaited()
        self.assertEqual(len(response), 1)
        self.assertIn("disabled", response[0].text.lower())

    async def test_allowed_tool_still_executes(self):
        client = object()
        callback = mcp_handlers.create_call_tool_handler(
            client, enabled_tools=["list_addons"]
        )
        expected = [TextContent(type="text", text="ok")]
        with patch.object(
            mcp_handlers, "handle_addon_tool",
            new_callable=AsyncMock, return_value=expected
        ) as handler:
            result = await callback("list_addons", {})
            handler.assert_awaited_once_with("list_addons", {}, client)
        self.assertEqual(result, expected)

    async def test_empty_allowlist_rejects_every_call(self):
        callback = mcp_handlers.create_call_tool_handler(
            object(), enabled_tools=[]
        )
        with patch.object(
            mcp_handlers, "handle_backup_tool", new_callable=AsyncMock
        ) as handler:
            result = await callback("delete_backup", {"slug": "backup"})
            handler.assert_not_awaited()
        self.assertIn("disabled", result[0].text.lower())

    async def test_secret_tool_arguments_are_not_logged(self):
        callback = mcp_handlers.create_call_tool_handler(
            object(), enabled_tools=["list_addons"]
        )
        with patch.object(
            mcp_handlers, "handle_addon_tool", new_callable=AsyncMock,
            return_value=[TextContent(type="text", text="ok")]
        ):
            with self.assertLogs("mcp_handlers", level="INFO") as captured:
                await callback(
                    "list_addons", {"password": "DO_NOT_LOG_THIS_SECRET"}
                )
        self.assertNotIn("DO_NOT_LOG_THIS_SECRET", "\n".join(captured.output))

    async def test_listing_and_execution_share_same_policy(self):
        enabled = ["list_addons"]
        listed = await mcp_handlers.create_list_tools_handler(
            object(), enabled_tools=enabled
        )()
        names = {tool.name for tool in listed}
        self.assertIn("list_addons", names)
        self.assertNotIn("uninstall_addon", names)


if __name__ == "__main__":
    unittest.main()
