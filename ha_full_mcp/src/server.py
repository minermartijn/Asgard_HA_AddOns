"""
Home Assistant MCP Server

A Model Context Protocol server for Home Assistant that provides:
- Full Home Assistant API access via WebSocket and REST
- Supervisor API access
- Entity and device management
- Add-on control and monitoring

This is the main entry point for the MCP server.
"""

import asyncio
import logging
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from config import load_config
from ha_client import HomeAssistantClient
from mcp_handlers import (
    create_list_tools_handler,
    create_call_tool_handler,
    create_list_resources_handler,
    create_read_resource_handler,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_sse_server(config, ha_client):
    """Run the server with SSE transport."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.middleware.cors import CORSMiddleware
    import uvicorn
    
    from routes import (
        create_sse_handler,
        create_sse_handler_with_path_key,
        create_messages_handler,
        create_messages_handler_with_path_key,
    )
    
    logger.info("Using SSE (Server-Sent Events) transport")
    
    # Create MCP server
    server = Server(config.server_name)
    
    # Register MCP handlers with enabled tools filter
    server.list_tools()(create_list_tools_handler(ha_client, config.enabled_tools))
    server.call_tool()(create_call_tool_handler(ha_client))
    server.list_resources()(create_list_resources_handler())
    server.read_resource()(create_read_resource_handler())
    
    # Create SSE transport with API key in path (Cloudflare-compatible)
    sse = SseServerTransport(f"/messages/{config.api_key}")
    
    # Create route handlers
    handle_sse = create_sse_handler(
        sse, server, config.api_key, config.server_name, config.server_version
    )
    handle_sse_with_key = create_sse_handler_with_path_key(
        sse, server, config.api_key, config.server_name, config.server_version
    )
    handle_messages = create_messages_handler(sse, config.api_key)
    handle_messages_with_key = create_messages_handler_with_path_key(sse, config.api_key)
    
    # Create Starlette app with all routes
    app = Starlette(
        routes=[
            Route("/sse", handle_sse, methods=["GET"]),
            Route("/messages", handle_messages, methods=["POST"]),
            Route("/sse/{api_key}", handle_sse_with_key, methods=["GET"]),
            Route("/messages/{api_key}", handle_messages_with_key, methods=["POST"]),
        ]
    )
    
    # Add CORS middleware
    # SECURITY NOTE: allow_origins=["*"] is permissive but acceptable because:
    # 1. All endpoints require API key authentication
    # 2. API key is cryptographically strong (256-bit)
    # 3. Server is typically behind Cloudflare or similar proxy
    # 4. HTTPS is enforced in production
    # For stricter security, configure specific origins in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    logger.info(f"Starting SSE server on {config.host}:{config.port}")
    logger.info(f"MCP SSE endpoint: http://{config.host}:{config.port}/sse")
    
    # Get tool count
    tools = await create_list_tools_handler(ha_client)()
    logger.info(f"Available tools: {len(tools)}")
    
    # Run the server
    uvicorn_config = uvicorn.Config(
        app,
        host=config.host,
        port=config.port,
        log_level="info"
    )
    server_instance = uvicorn.Server(uvicorn_config)
    await server_instance.serve()


async def run_stdio_server(config, ha_client):
    """Run the server with stdio transport."""
    logger.info("Using stdio transport")
    
    # Create MCP server
    server = Server(config.server_name)
    
    # Register MCP handlers with enabled tools filter
    server.list_tools()(create_list_tools_handler(ha_client, config.enabled_tools))
    server.call_tool()(create_call_tool_handler(ha_client))
    server.list_resources()(create_list_resources_handler())
    server.read_resource()(create_read_resource_handler())
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=config.server_name,
                server_version=config.server_version,
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )


async def main():
    """Main entry point for the MCP server."""
    # Load configuration
    config = load_config()
    
    # Initialize Home Assistant client
    ha_client = HomeAssistantClient(ha_token=config.ha_token)
    
    logger.info("Starting Home Assistant MCP Server")
    
    # Run appropriate transport
    if config.transport_type == "sse":
        await run_sse_server(config, ha_client)
    else:
        await run_stdio_server(config, ha_client)


if __name__ == "__main__":
    asyncio.run(main())
