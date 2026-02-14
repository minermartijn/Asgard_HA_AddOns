"""
Authentication handlers for Home Assistant MCP Server.

Supports multiple authentication methods:
1. Path parameter (recommended for Cloudflare)
2. Query parameter
3. Authorization header (Bearer token)
4. X-API-Key header

Security: Uses constant-time comparison to prevent timing attacks.
"""

import logging
import secrets
from starlette.requests import Request

logger = logging.getLogger(__name__)


def verify_api_key(request: Request, api_key: str) -> bool:
    """
    Verify API key from request headers or query parameters.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        request: Starlette request object
        api_key: Expected API key
        
    Returns:
        True if authentication succeeds, False otherwise
    """
    # Check query parameter first (for Cloudflare compatibility)
    query_key = request.query_params.get("api_key", "")
    if query_key and secrets.compare_digest(query_key, api_key):
        return True
    
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if secrets.compare_digest(token, api_key):
            return True
    
    # Check X-API-Key header
    request_key = request.headers.get("X-API-Key", "")
    if request_key and secrets.compare_digest(request_key, api_key):
        return True
    
    return False


def verify_path_api_key(request: Request, api_key: str) -> bool:
    """
    Verify API key from path parameter.
    
    This is the recommended method for Cloudflare deployments as path
    parameters survive proxy forwarding.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        request: Starlette request object
        api_key: Expected API key
        
    Returns:
        True if authentication succeeds, False otherwise
    """
    path_key = request.path_params.get("api_key", "")
    if not path_key:
        return False
    return secrets.compare_digest(path_key, api_key)
