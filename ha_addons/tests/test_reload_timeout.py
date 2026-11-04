"""Tests for ha_addons reload_addons timeout resilience and catalog availability."""

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add src to path
src_dir = Path(__file__).parents[1] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from ha_client import HomeAssistantClient
from tools.addon_tools import handle_addon_tool, get_addon_tool_definitions
from mcp_handlers import create_list_tools_handler, create_call_tool_handler


class ReloadAddonsClientTests(unittest.IsolatedAsyncioTestCase):
    """Test HomeAssistantClient reload_addons non-blocking behavior."""

    async def asyncSetUp(self):
        self.client = HomeAssistantClient(ha_token="mock_token")

    async def test_reload_addons_fast_completion(self):
        """When Supervisor reload is fast, it returns completed status."""
        self.client._make_request = AsyncMock(return_value={"result": "ok"})
        
        result = await self.client.reload_addons(wait_seconds=2.0)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"], "ok")

    async def test_reload_addons_slow_backgrounds_and_allows_concurrent_calls(self):
        """When Supervisor reload takes long, it does not block and returns in_progress.
        Subsequent calls to get_addon_info succeed immediately."""
        async def slow_reload(*args, **kwargs):
            await asyncio.sleep(1.0)
            return {"result": "ok"}

        # Mock reload to be slow, while get_addon_info is fast
        async def mock_make_request(method, url, **kwargs):
            if "/addons/reload" in url:
                return await slow_reload(method, url, **kwargs)
            elif "/addons/core_ssh/info" in url:
                return {"data": {"name": "Terminal & SSH", "version": "9.7.1", "state": "started"}}
            elif "/addons" in url:
                return {"data": {"addons": [{"slug": "core_ssh", "name": "Terminal & SSH"}]}}
            return {}

        self.client._make_request = AsyncMock(side_effect=mock_make_request)

        # Trigger reload with 0.1s wait timeout
        start = asyncio.get_event_loop().time()
        reload_result = await self.client.reload_addons(wait_seconds=0.1)
        duration = asyncio.get_event_loop().time() - start

        # Should return in ~0.1s without waiting for 1.0s
        self.assertLess(duration, 0.5)
        self.assertEqual(reload_result["status"], "in_progress")
        self.assertIn("initiated in background", reload_result["message"])

        # Check status is in_progress
        status = await self.client.get_reload_status()
        self.assertEqual(status["status"], "in_progress")

        # Immediately call get_addon_info while reload is still running in background
        info = await self.client.get_addon_info("core_ssh")
        self.assertEqual(info["name"], "Terminal & SSH")
        self.assertEqual(info["version"], "9.7.1")

        # Immediately call list_addons while reload is still running in background
        addons = await self.client.list_addons()
        self.assertEqual(len(addons), 1)
        self.assertEqual(addons[0]["slug"], "core_ssh")

        # Wait for the background reload to finish
        await asyncio.sleep(1.1)

        # Check status is now completed
        status_after = await self.client.get_reload_status()
        self.assertEqual(status_after["status"], "completed")


class ReloadAddonsToolTests(unittest.IsolatedAsyncioTestCase):
    """Test MCP tool layer execution for reload_addons."""

    async def asyncSetUp(self):
        self.client = HomeAssistantClient(ha_token="mock_token")

    async def test_tool_catalog_contains_reload_addons(self):
        """Tool definitions list contains reload_addons with non-blocking schema."""
        tools = get_addon_tool_definitions()
        reload_tool = next((t for t in tools if t.name == "reload_addons"), None)
        self.assertIsNotNone(reload_tool)
        self.assertIn("wait_timeout", reload_tool.inputSchema["properties"])
        self.assertIn("wait", reload_tool.inputSchema["properties"])

    async def test_handle_addon_tool_reload_in_progress_and_subsequent_get_info(self):
        """handle_addon_tool for reload_addons returns clean markdown when in_progress.
        Subsequent get_addon_info executes without error."""
        async def slow_request(method, url, **kwargs):
            if "/addons/reload" in url:
                await asyncio.sleep(1.0)
                return {"result": "ok"}
            elif "/addons/ha_full_mcp/info" in url:
                return {
                    "data": {
                        "name": "HA Full MCP Server",
                        "slug": "ha_full_mcp",
                        "version": "1.10.3",
                        "version_latest": "1.10.3",
                        "state": "started",
                    }
                }
            return {}

        self.client._make_request = AsyncMock(side_effect=slow_request)

        # Call reload_addons tool with wait_timeout=0.1
        reload_res = await handle_addon_tool(
            "reload_addons",
            {"wait_timeout": 0.1, "wait": True},
            self.client,
        )
        self.assertEqual(len(reload_res), 1)
        self.assertIn("running in the background", reload_res[0].text)
        self.assertIn("Your MCP connection remains active", reload_res[0].text)

        # Subsequent get_addon_info tool call succeeds immediately
        info_res = await handle_addon_tool(
            "get_addon_info",
            {"addon_slug": "ha_full_mcp"},
            self.client,
        )
        self.assertEqual(len(info_res), 1)
        self.assertIn("HA Full MCP Server", info_res[0].text)
        self.assertIn("1.10.3", info_res[0].text)

        # Verify tool catalog remains available through handler
        list_handler = create_list_tools_handler(self.client)
        available_tools = await list_handler()
        tool_names = [t.name for t in available_tools]
        self.assertIn("reload_addons", tool_names)
        self.assertIn("get_addon_info", tool_names)
        self.assertIn("update_addon", tool_names)


class StreamableHTTPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """End-to-end integration test over Streamable HTTP transport."""

    async def test_streamable_http_reload_and_subsequent_catalog(self):
        """Verify that over Streamable HTTP, a long reload_addons does not break session
        and subsequent tools/list and get_addon_info requests succeed."""
        import httpx
        from mcp.server import Server
        try:
            from mcp.server.streamable_http import StreamableHTTPSessionManager
        except ImportError:
            from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.applications import Starlette
        from starlette.routing import Route
        from routes import create_streamable_http_handler
        import uvicorn

        client = HomeAssistantClient(ha_token="mock_token")

        # Mock slow reload, fast info
        async def mock_req(method, url, **kwargs):
            if "/addons/reload" in url:
                await asyncio.sleep(0.8)
                return {"result": "ok"}
            elif "/addons/ha_full_mcp/info" in url:
                return {
                    "data": {
                        "name": "HA Full MCP Server",
                        "slug": "ha_full_mcp",
                        "version": "1.10.3",
                        "state": "started",
                    }
                }
            return {}

        client._make_request = AsyncMock(side_effect=mock_req)

        server = Server("test-lifeboat")
        server.list_tools()(create_list_tools_handler(client))
        server.call_tool()(create_call_tool_handler(client))

        api_key = "test-secret-key-12345"
        session_manager = StreamableHTTPSessionManager(server, session_idle_timeout=60)
        handler = create_streamable_http_handler(session_manager, api_key)

        app = Starlette(routes=[Route("/mcp", handler, methods=["GET", "POST", "DELETE"])])

        config = uvicorn.Config(app, host="127.0.0.1", port=8915, log_level="error")
        uv_server = uvicorn.Server(config)
        server_task = asyncio.create_task(uv_server.serve())
        await asyncio.sleep(0.3)

        try:
            async with session_manager.run():
                async with httpx.AsyncClient(base_url="http://127.0.0.1:8915") as http_client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Accept": "application/json, text/event-stream",
                    }

                    # 1. Initialize session
                    init_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "test-paperclip", "version": "1.0"},
                        },
                    }
                    r = await http_client.post("/mcp", json=init_payload, headers=headers)
                    self.assertEqual(r.status_code, 200)
                    session_id = r.headers.get("mcp-session-id")
                    self.assertIsNotNone(session_id)
                    headers["mcp-session-id"] = session_id

                    # 2. Initialized notification
                    await http_client.post(
                        "/mcp",
                        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                        headers=headers,
                    )

                    # 3. List tools before reload
                    r_tools1 = await http_client.post(
                        "/mcp",
                        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                        headers=headers,
                    )
                    self.assertEqual(r_tools1.status_code, 200)
                    self.assertIn("reload_addons", r_tools1.text)

                    # 4. Call reload_addons with wait_timeout=0.1
                    call_reload = {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "reload_addons",
                            "arguments": {"wait_timeout": 0.1, "wait": True},
                        },
                    }
                    r_call = await http_client.post("/mcp", json=call_reload, headers=headers, timeout=5.0)
                    self.assertEqual(r_call.status_code, 200)
                    self.assertIn("background", r_call.text)

                    # 5. Immediately call get_addon_info on the same session
                    call_info = {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {
                            "name": "get_addon_info",
                            "arguments": {"addon_slug": "ha_full_mcp"},
                        },
                    }
                    r_info = await http_client.post("/mcp", json=call_info, headers=headers, timeout=5.0)
                    self.assertEqual(r_info.status_code, 200)
                    self.assertIn("HA Full MCP Server", r_info.text)

                    # 6. Immediately verify tool catalog is STILL available
                    r_tools2 = await http_client.post(
                        "/mcp",
                        json={"jsonrpc": "2.0", "id": 5, "method": "tools/list"},
                        headers=headers,
                        timeout=5.0,
                    )
                    self.assertEqual(r_tools2.status_code, 200)
                    self.assertIn("reload_addons", r_tools2.text)
                    self.assertIn("get_addon_info", r_tools2.text)

        finally:
            uv_server.should_exit = True
            await server_task

    async def test_streamable_http_client_timeout_abort_preserves_session(self):
        """Even if an aggressive client times out (e.g. 0.05s) on a tool call,
        the server connection handles cancellation gracefully and subsequent calls succeed."""
        import httpx
        from mcp.server import Server
        try:
            from mcp.server.streamable_http import StreamableHTTPSessionManager
        except ImportError:
            from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.applications import Starlette
        from starlette.routing import Route
        from routes import create_streamable_http_handler
        import uvicorn

        client = HomeAssistantClient(ha_token="mock_token")

        async def slow_supervisor(method, url, **kwargs):
            if "/addons/reload" in url:
                await asyncio.sleep(2.0)
                return {"result": "ok"}
            elif "/addons/ha_full_mcp/info" in url:
                return {"data": {"name": "HA Full MCP Server", "slug": "ha_full_mcp", "version": "1.10.3"}}
            return {}

        client._make_request = AsyncMock(side_effect=slow_supervisor)

        server = Server("test-lifeboat-abort")
        server.list_tools()(create_list_tools_handler(client))
        server.call_tool()(create_call_tool_handler(client))

        api_key = "test-secret-key-54321"
        session_manager = StreamableHTTPSessionManager(server, session_idle_timeout=60)
        handler = create_streamable_http_handler(session_manager, api_key)

        app = Starlette(routes=[Route("/mcp", handler, methods=["GET", "POST", "DELETE"])])

        config = uvicorn.Config(app, host="127.0.0.1", port=8916, log_level="error")
        uv_server = uvicorn.Server(config)
        server_task = asyncio.create_task(uv_server.serve())
        await asyncio.sleep(0.3)

        try:
            async with session_manager.run():
                async with httpx.AsyncClient(base_url="http://127.0.0.1:8916") as http_client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Accept": "application/json, text/event-stream",
                    }

                    # Initialize
                    r = await http_client.post(
                        "/mcp",
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {},
                                "clientInfo": {"name": "test-abort", "version": "1.0"},
                            },
                        },
                        headers=headers,
                    )
                    session_id = r.headers.get("mcp-session-id")
                    headers["mcp-session-id"] = session_id

                    await http_client.post(
                        "/mcp",
                        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                        headers=headers,
                    )

                    # Simulate client with very short timeout aborting a request
                    try:
                        await http_client.post(
                            "/mcp",
                            json={
                                "jsonrpc": "2.0",
                                "id": 2,
                                "method": "tools/call",
                                "params": {
                                    "name": "reload_addons",
                                    "arguments": {"wait_timeout": 1.0, "wait": True},
                                },
                            },
                            headers=headers,
                            timeout=0.05,
                        )
                    except (httpx.ReadTimeout, httpx.TimeoutException):
                        pass

                    # Small pause for cancellation to propagate
                    await asyncio.sleep(0.1)

                    # Subsequent tool call and tool catalog must STILL succeed on this session!
                    r_tools = await http_client.post(
                        "/mcp",
                        json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
                        headers=headers,
                        timeout=5.0,
                    )
                    self.assertEqual(r_tools.status_code, 200)
                    self.assertIn("get_addon_info", r_tools.text)

                    r_info = await http_client.post(
                        "/mcp",
                        json={
                            "jsonrpc": "2.0",
                            "id": 4,
                            "method": "tools/call",
                            "params": {
                                "name": "get_addon_info",
                                "arguments": {"addon_slug": "ha_full_mcp"},
                            },
                        },
                        headers=headers,
                        timeout=5.0,
                    )
                    self.assertEqual(r_info.status_code, 200)
                    self.assertIn("HA Full MCP Server", r_info.text)

        finally:
            uv_server.should_exit = True
            await server_task

    async def test_sse_reconnect_clean_lifespan(self):
        """Verify that SSE client disconnect does not raise unhandled exceptions
        and allows seamless reconnection."""
        from httpx_sse import aconnect_sse
        from mcp.server.sse import SseServerTransport
        import httpx
        from mcp.server import Server
        from starlette.applications import Starlette
        from starlette.routing import Route
        from routes import create_sse_handler, create_messages_handler
        import uvicorn

        client = HomeAssistantClient(ha_token="mock_token")
        client._make_request = AsyncMock(return_value={"data": {"addons": []}})

        server = Server("test-sse-reconnect")
        server.list_tools()(create_list_tools_handler(client))
        server.call_tool()(create_call_tool_handler(client))

        api_key = "test-secret-sse-key"
        sse = SseServerTransport(f"/messages/{api_key}")
        handle_sse = create_sse_handler(sse, server, api_key, "test-sse-reconnect", "1.3.1")
        handle_msg = create_messages_handler(sse, api_key)

        app = Starlette(routes=[
            Route("/sse", handle_sse, methods=["GET"]),
            Route(f"/messages/{api_key}", handle_msg, methods=["POST"]),
        ])

        config = uvicorn.Config(app, host="127.0.0.1", port=8917, log_level="error")
        uv_server = uvicorn.Server(config)
        server_task = asyncio.create_task(uv_server.serve())
        await asyncio.sleep(0.3)

        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-sse", "version": "1.0"},
            },
        }

        try:
            async with httpx.AsyncClient(base_url="http://127.0.0.1:8917") as http_client:
                # Session 1: connect and disconnect
                async with aconnect_sse(
                    http_client, "GET", "/sse", headers={"Authorization": f"Bearer {api_key}"}
                ) as sse_1:
                    sse_iter = sse_1.aiter_sse()
                    ep_event = await anext(sse_iter)
                    endpoint = ep_event.data

                    await http_client.post(
                        endpoint,
                        json=init_payload,
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    await anext(sse_iter)
                    # Disconnect abruptly

                await asyncio.sleep(0.2)

                # Session 2: reconnect and list tools
                async with aconnect_sse(
                    http_client, "GET", "/sse", headers={"Authorization": f"Bearer {api_key}"}
                ) as sse_2:
                    sse_iter2 = sse_2.aiter_sse()
                    ep_event2 = await anext(sse_iter2)
                    endpoint2 = ep_event2.data

                    await http_client.post(
                        endpoint2,
                        json=init_payload,
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    await anext(sse_iter2)

                    await http_client.post(
                        endpoint2,
                        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                        headers={"Authorization": f"Bearer {api_key}"},
                    )

                    await http_client.post(
                        endpoint2,
                        json={"jsonrpc": "2.0", "id": 10, "method": "tools/list"},
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    tools_event = await anext(sse_iter2)
                    self.assertIn("reload_addons", tools_event.data)
                    self.assertIn("get_addon_info", tools_event.data)

        finally:
            uv_server.should_exit = True
            await server_task


if __name__ == "__main__":
    unittest.main()
