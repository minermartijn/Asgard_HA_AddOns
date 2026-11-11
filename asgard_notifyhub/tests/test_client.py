"""Tests for Home Assistant Core API client and domain security boundaries."""

import asyncio
from app.client import (
    ALLOWED_DOMAINS,
    DemoHomeAssistantClient,
    RestHomeAssistantClient,
)


def test_allowed_domains():
    assert "notify" in ALLOWED_DOMAINS
    assert "persistent_notification" in ALLOWED_DOMAINS
    assert "shell_command" not in ALLOWED_DOMAINS
    assert "homeassistant" not in ALLOWED_DOMAINS


def test_demo_client_operations():
    client = DemoHomeAssistantClient()

    # Discover services
    services = asyncio.run(client.discover_services())
    assert len(services) >= 3
    assert any(s.ha_domain == "notify" for s in services)
    assert any(s.ha_domain == "persistent_notification" for s in services)

    # Valid notify call
    ok, err = asyncio.run(
        client.send_notification(
            domain="notify",
            service="mobile_app_phone",
            title="Test",
            message="Hello",
        )
    )
    assert ok is True
    assert err is None
    assert len(client.dispatched_calls) == 1

    # Call with unauthorized domain should return Security Violation
    ok_bad, err_bad = asyncio.run(
        client.send_notification(
            domain="shell_command",
            service="execute_root",
            title="Exploit",
            message="malicious",
        )
    )
    assert ok_bad is False
    assert "Security Violation" in (err_bad or "")


def test_rest_client_security_boundary():
    client = RestHomeAssistantClient(core_api_url="http://supervisor/core/api", token="test_token")

    # Unauthorized domain is blocked locally before network request
    ok, err = asyncio.run(
        client.send_notification(
            domain="system",
            service="reboot",
            title="Attack",
            message="danger",
        )
    )
    assert ok is False
    assert "Security Violation" in (err or "")
