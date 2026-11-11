"""Tests for Home Assistant Core API client and domain security boundaries."""

import asyncio
import httpx
import pytest
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
    assert client.last_error is None

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


def test_rest_client_missing_token():
    client = RestHomeAssistantClient(core_api_url="http://supervisor/core/api", token=None)
    services = asyncio.run(client.discover_services())
    assert services == []
    assert client.last_error is not None
    assert "Supervisor token not available" in client.last_error

    ok, err = asyncio.run(
        client.send_notification(
            domain="notify",
            service="mobile_app",
            title="Test",
            message="Msg",
        )
    )
    assert ok is False
    assert "No Supervisor token provided" in (err or "")


def test_rest_client_http_errors_and_entities():
    # Mock transport responding to /services with 401
    def handler_401(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})

    transport_401 = httpx.MockTransport(handler_401)
    client_401 = RestHomeAssistantClient("http://supervisor/core/api", token="bad_token", transport=transport_401)
    svcs = asyncio.run(client_401.discover_services())
    assert svcs == []
    assert "401 Unauthorized" in client_401.last_error

    # Mock transport responding to /services with 403
    def handler_403(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Forbidden"})

    transport_403 = httpx.MockTransport(handler_403)
    client_403 = RestHomeAssistantClient("http://supervisor/core/api", token="bad_token", transport=transport_403)
    svcs_403 = asyncio.run(client_403.discover_services())
    assert svcs_403 == []
    assert "403 Forbidden" in client_403.last_error

    # Mock transport successfully discovering services AND notify entities
    def handler_success(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/core/api/services":
            return httpx.Response(
                200,
                json=[
                    {
                        "domain": "notify",
                        "services": {
                            "notify": {"name": "Notify Service", "description": "General broadcast"},
                            "persistent_notification": {"name": "HA Notification", "description": "Web banner"},
                        },
                    },
                    {
                        "domain": "persistent_notification",
                        "services": {
                            "create": {"name": "Create Notification", "description": "Creates notification"},
                        },
                    },
                ],
            )
        elif request.url.path == "/core/api/states":
            return httpx.Response(
                200,
                json=[
                    {
                        "entity_id": "notify.living_room_tv",
                        "state": "idle",
                        "attributes": {"friendly_name": "Living Room TV Notification"},
                    },
                    {
                        "entity_id": "light.kitchen",
                        "state": "on",
                    },
                ],
            )
        return httpx.Response(404)

    transport_success = httpx.MockTransport(handler_success)
    client_ok = RestHomeAssistantClient("http://supervisor/core/api", token="valid_token", transport=transport_success)
    svcs_ok = asyncio.run(client_ok.discover_services())
    assert len(svcs_ok) == 4
    assert any(s.ha_service == "living_room_tv" and s.target_type == "entity" for s in svcs_ok)
    assert any(s.ha_domain == "persistent_notification" and s.ha_service == "create" for s in svcs_ok)
    assert client_ok.last_error is None


def test_rest_client_known_entity_dispatch():
    """Verify that known notify entities route directly to notify.send_message."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json
        calls.append({
            "path": request.url.path,
            "json": json.loads(request.content.decode("utf-8")),
        })
        if request.url.path == "/core/api/services/notify/send_message":
            return httpx.Response(200, json=[{"success": True}])
        return httpx.Response(400, text="Bad Request")

    transport = httpx.MockTransport(handler)
    client = RestHomeAssistantClient("http://supervisor/core/api", token="tok", transport=transport)
    client._known_entities.add("mart_s25")
    client._known_entities.add("notify.mart_s25")

    ok, err = asyncio.run(
        client.send_notification(
            domain="notify",
            service="mart_s25",
            title="Test",
            message="Hello Martijn",
            data={"channel": "priority"},
        )
    )
    assert ok is True
    assert err is None
    assert len(calls) == 1
    assert calls[0]["path"] == "/core/api/services/notify/send_message"
    assert calls[0]["json"]["entity_id"] == "notify.mart_s25"
    assert calls[0]["json"]["message"] == "Hello Martijn"
    assert calls[0]["json"]["title"] == "Test"
    assert calls[0]["json"]["data"] == {"channel": "priority"}


def test_rest_client_unknown_entity_fallback_on_400():
    """Verify that when calling a notify service returns 400 Bad Request, it falls back to notify.send_message."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json
        calls.append({
            "path": request.url.path,
            "json": json.loads(request.content.decode("utf-8")),
        })
        if request.url.path == "/core/api/services/notify/mart_s25":
            return httpx.Response(400, text="400: Bad Request")
        elif request.url.path == "/core/api/services/notify/send_message":
            return httpx.Response(200, json=[{"success": True}])
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    client = RestHomeAssistantClient("http://supervisor/core/api", token="tok", transport=transport)

    ok, err = asyncio.run(
        client.send_notification(
            domain="notify",
            service="mart_s25",
            title="Alert",
            message="Door opened",
        )
    )
    assert ok is True
    assert err is None
    assert len(calls) == 2
    assert calls[0]["path"] == "/core/api/services/notify/mart_s25"
    assert calls[1]["path"] == "/core/api/services/notify/send_message"
    assert calls[1]["json"]["entity_id"] == "notify.mart_s25"
    assert "mart_s25" in client._known_entities
