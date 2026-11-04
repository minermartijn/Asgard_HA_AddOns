"""
Configuration management for HA Addon MCP Server (Lifeboat).
"""

import os
import json
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
    server_name: str = "ha-addon-mcp-server"
    server_version: str = "1.3.2"


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


def load_config() -> ServerConfig:
    """Load configuration from /data/options.json (Home Assistant) with env fallback."""
    options_data: dict = {}
    options_file = os.environ.get("OPTIONS_PATH", "/data/options.json")
    if os.path.exists(options_file):
        try:
            with open(options_file, "r", encoding="utf-8") as f:
                options_data = json.load(f)
            logger.info(f"Loaded add-on configuration from {options_file}")
        except Exception as e:
            logger.warning(f"Could not read {options_file}: {e}")

    # Base options (options.json takes precedence, falls back to env vars)
    ha_token = options_data.get("ha_token") or os.environ.get("HA_TOKEN")
    api_key = str(options_data.get("api_key") or os.environ.get("API_KEY", "")).strip()

    raw_transport = str(options_data.get("transport") or os.environ.get("TRANSPORT", "sse")).lower().strip()
    if raw_transport in ("streamable-http", "streamable_http", "streamablehttp"):
        transport_type = "streamable-http"
    elif raw_transport == "stdio":
        transport_type = "stdio"
    elif raw_transport in ("all", "both"):
        transport_type = "all"
    else:
        transport_type = "sse"

    host = str(options_data.get("host") or os.environ.get("HOST", "0.0.0.0"))
    try:
        port = int(options_data.get("port") or os.environ.get("PORT", "8015"))
    except (ValueError, TypeError):
        port = 8015
    
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
