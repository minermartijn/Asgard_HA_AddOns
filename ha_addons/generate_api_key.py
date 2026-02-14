#!/usr/bin/env python3
"""
API Key Generator for Home Assistant MCP Server

Generates a secure random API key that can be used in the add-on configuration.
"""

import secrets

def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)

if __name__ == "__main__":
    api_key = generate_api_key()
    print("=" * 80)
    print("Generated API Key for Home Assistant MCP Server:")
    print()
    print(f"  {api_key}")
    print()
    print("Add this to your add-on configuration:")
    print()
    print("  api_key: " + api_key)
    print()
    print("=" * 80)
