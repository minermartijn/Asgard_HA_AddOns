"""
Route handlers for Home Assistant MCP Server SSE transport.
"""

import logging
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions
from mcp.server.sse import SseServerTransport

from auth import verify_api_key, verify_path_api_key

logger = logging.getLogger(__name__)


class AlreadySentResponse(Response):
    """
    Special Response class for handlers that send responses directly via ASGI.
    
    When sse.handle_post_message() is called, it sends the response directly
    through the ASGI send callable. However, Starlette's routing expects
    handlers to return a Response object. This class satisfies that requirement
    without actually sending anything (since the response was already sent).
    """
    
    async def __call__(self, scope, receive, send):
        """Don't send anything - response was already sent by the handler."""
        pass  # Do nothing - response already sent via ASGI


def create_sse_handler(
    sse: SseServerTransport,
    server: Server,
    api_key: str,
    server_name: str,
    server_version: str,
):
    """
    Create SSE connection handler with query/header authentication.
    
    Args:
        sse: SSE transport instance
        server: MCP server instance
        api_key: Expected API key
        server_name: Server name for initialization
        server_version: Server version for initialization
        
    Returns:
        Async handler function
    """
    async def handle_sse(request: Request):
        """Handle SSE connection - the context manager handles the response"""
        # Verify API key
        if not verify_api_key(request, api_key):
            logger.warning(f"Unauthorized SSE connection attempt from {request.client.host}")
            return JSONResponse(
                {"error": "Unauthorized - Invalid or missing API key"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send
        ) as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name=server_name,
                server_version=server_version,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
            await server.run(
                read_stream,
                write_stream,
                init_options,
            )
    
    return handle_sse


def create_sse_handler_with_path_key(
    sse: SseServerTransport,
    server: Server,
    api_key: str,
    server_name: str,
    server_version: str,
):
    """
    Create SSE connection handler with path-based authentication.
    
    This is the recommended handler for Cloudflare deployments.
    
    Args:
        sse: SSE transport instance
        server: MCP server instance
        api_key: Expected API key
        server_name: Server name for initialization
        server_version: Server version for initialization
        
    Returns:
        Async handler function
    """
    async def handle_sse_with_key(request: Request):
        """Handle SSE connection with API key in path"""
        if not verify_path_api_key(request, api_key):
            logger.warning(f"Unauthorized SSE connection attempt from {request.client.host}")
            return JSONResponse(
                {"error": "Unauthorized - Invalid or missing API key"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send
        ) as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name=server_name,
                server_version=server_version,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
            await server.run(
                read_stream,
                write_stream,
                init_options,
            )
    
    return handle_sse_with_key


def create_messages_handler(sse: SseServerTransport, api_key: str):
    """
    Create message handler with query/header authentication.
    
    Args:
        sse: SSE transport instance
        api_key: Expected API key
        
    Returns:
        Async handler function
    """
    async def handle_messages(request: Request):
        """Handle POST messages from client"""
        if not verify_api_key(request, api_key):
            session_id = request.query_params.get("session_id")
            logger.warning(f"Unauthorized message attempt from {request.client.host}, session: {session_id}")
            logger.warning(f"Query params: {dict(request.query_params)}")
            logger.warning(f"Headers: Authorization={request.headers.get('Authorization', 'NONE')}, X-API-Key={request.headers.get('X-API-Key', 'NONE')}")
            return JSONResponse(
                {"error": "Unauthorized - Invalid or missing API key"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Handle the message - this function sends response directly via ASGI
        await sse.handle_post_message(request.scope, request.receive, request._send)
        
        # Return AlreadySentResponse to satisfy Starlette routing
        # (actual response was already sent above)
        return AlreadySentResponse()
    
    return handle_messages


def create_messages_handler_with_path_key(sse: SseServerTransport, api_key: str):
    """
    Create message handler with path-based authentication.
    
    This is the recommended handler for Cloudflare deployments.
    
    Args:
        sse: SSE transport instance
        api_key: Expected API key
        
    Returns:
        Async handler function
    """
    async def handle_messages_with_key(request: Request):
        """Handle POST messages with API key in path"""
        if not verify_path_api_key(request, api_key):
            logger.warning(f"Unauthorized message attempt from {request.client.host}")
            return JSONResponse(
                {"error": "Unauthorized - Invalid or missing API key"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Handle the message - this function sends response directly via ASGI
        await sse.handle_post_message(request.scope, request.receive, request._send)
        
        # Return AlreadySentResponse to satisfy Starlette routing
        # (actual response was already sent above)
        return AlreadySentResponse()
    
    return handle_messages_with_key
