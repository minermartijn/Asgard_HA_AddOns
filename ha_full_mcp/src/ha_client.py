"""
Home Assistant API Client for MCP Server.

This module provides a backward-compatible import for the refactored API client.
The actual implementation is now split across multiple modules in src/api/ for better maintainability.
"""
from api import HomeAssistantClient

__all__ = ['HomeAssistantClient']
