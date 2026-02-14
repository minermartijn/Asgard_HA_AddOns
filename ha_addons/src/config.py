"""
Configuration management for Home Assistant MCP Server.
"""

import os
import secrets
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Server configuration."""
    ha_token: str
    api_key: str
    transport_type: str
    host: str
    port: int
    server_name: str = "home-assistant-mcp"
    server_version: str = "0.6.0"


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


def load_config() -> ServerConfig:
    """Load configuration from environment variables."""
    # Get configuration from environment
    ha_token = os.environ.get("HA_TOKEN")
    api_key = os.environ.get("API_KEY", "").strip()
    transport_type = os.environ.get("TRANSPORT", "sse").lower()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8010"))
    
    # Generate API key if not provided
    if not api_key:
        api_key = generate_api_key()
        logger.warning("=" * 80)
        logger.warning("NO API KEY CONFIGURED - Generated new API key:")
        logger.warning(f"API_KEY: {api_key}")
        logger.warning("Please save this key and add it to your add-on configuration!")
        logger.warning("=" * 80)
    
    logger.info("Configuration loaded:")
    logger.info(f"  HA Token configured: {bool(ha_token)}")
    logger.info(f"  API Key configured: {bool(api_key)}")
    logger.info(f"  Transport type: {transport_type}")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    
    return ServerConfig(
        ha_token=ha_token,
        api_key=api_key,
        transport_type=transport_type,
        host=host,
        port=port,
    )
