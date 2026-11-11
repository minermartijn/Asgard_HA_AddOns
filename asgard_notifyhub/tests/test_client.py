"""Tests for Home Assistant Core API client and domain security boundaries."""

import asyncio
import json
import httpx
import pytest
from app.client import (
    ALLOWED_DOMAINS,
    DemoHomeAssistantClient,
    RestHomeAssistantClient,
    is_allowed_action,
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


def _ha_mock(post_handler, services=None, states=None):
    """Build a MockTransport emulating HA discovery plus a custom POST handler."""
    calls = []
    services = services if services is not None else [
        {"domain": "notify", "services": {
            "mobile_app_galaxy_watch5_fhyw": {"name": "Send a notification via mobile_app_galaxy_watch5_fhyw"},
            "send_message": {"name": "Send a notification message"},
            "persistent_notification": {"name": "Send a persistent notification"},
        }},
        {"domain": "persistent_notification", "services": {
            "create": {"name": "Create"}, "dismiss": {"name": "Dismiss"}, "dismiss_all": {"name": "Dismiss all"},
        }},
        {"domain": "light", "services": {"turn_on": {}}},
    ]
    states = states if states is not None else [
        {"entity_id": "notify.galaxy_watch5_fhyw", "state": "unknown",
         "attributes": {"friendly_name": "Galaxy Watch5 (FHYW)"}},
        {"entity_id": "notify.mart_s25", "state": "unknown", "attributes": {"friendly_name": "Mart_S25"}},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/core/api/services":
            return httpx.Response(200, json=services)
        if request.method == "GET" and request.url.path == "/core/api/states":
            return httpx.Response(200, json=states)
        body = json.loads(request.content.decode("utf-8")) if request.content else None
        calls.append({"path": request.url.path, "json": body})
        return post_handler(request)

    return httpx.MockTransport(handler), calls


def test_discovery_applies_action_level_allowlist():
    transport, _ = _ha_mock(lambda r: httpx.Response(200, json=[]))
    client = RestHomeAssistantClient("http://supervisor/core/api", token="tok", transport=transport)
    svcs = asyncio.run(client.discover_services())
    names = {s.full_name for s in svcs}
    assert "persistent_notification.create" in names
    assert "persistent_notification.dismiss" not in names
    assert "persistent_notification.dismiss_all" not in names
    assert "notify.send_message" not in names
    assert "light.turn_on" not in names
    assert "notify.mobile_app_galaxy_watch5_fhyw" in names
    watch_entity = next(s for s in svcs if s.full_name == "notify.galaxy_watch5_fhyw")
    assert watch_entity.target_type == "entity"
    assert watch_entity.ha_state == "unknown"


def test_is_allowed_action_matrix():
    assert is_allowed_action("notify", "mobile_app_mart_s25")
    assert is_allowed_action("notify", "mart_s25")
    assert is_allowed_action("persistent_notification", "create")
    assert not is_allowed_action("persistent_notification", "dismiss")
    assert not is_allowed_action("persistent_notification", "dismiss_all")
    assert not is_allowed_action("notify", "send_message")
    assert not is_allowed_action("notify", "../../services/light")
    assert not is_allowed_action("shell_command", "anything")


def test_entity_dispatch_uses_send_message_without_data():
    transport, calls = _ha_mock(lambda r: httpx.Response(200, json=[]))
    client = RestHomeAssistantClient("http://supervisor/core/api", token="tok", transport=transport)
    ok, err = asyncio.run(client.send_notification(
        domain="notify", service="mart_s25", title="Test", message="Hello", data={"channel": "x"},
    ))
    assert ok is True and err is None
    assert len(calls) == 1
    assert calls[0]["path"] == "/core/api/services/notify/send_message"
    assert calls[0]["json"] == {"entity_id": "notify.mart_s25", "message": "Hello", "title": "Test"}


def test_legacy_service_dispatch_keeps_data():
    transport, calls = _ha_mock(lambda r: httpx.Response(200, json=[]))
    client = RestHomeAssistantClient("http://supervisor/core/api", token="tok", transport=transport)
    ok, _ = asyncio.run(client.send_notification(
        domain="notify", service="mobile_app_galaxy_watch5_fhyw", title=None, message="Hi", data={"ttl": 0},
    ))
    assert ok is True
    assert len(calls) == 1
    assert calls[0]["path"] == "/core/api/services/notify/mobile_app_galaxy_watch5_fhyw"
    assert calls[0]["json"] == {"message": "Hi", "data": {"ttl": 0}}


def test_galaxy_watch_entity_http_500_is_reported_without_retry():
    """Reproduces the real-world failure: notify.galaxy_watch5_fhyw -> HTTP 500.

    The client must make exactly one call (no fallback that could duplicate the
    notification) and return an actionable message pointing at the mobile_app action.
    """
    def post(request):
        if request.url.path == "/core/api/services/notify/send_message":
            return httpx.Response(500, text="500 Internal Server Error")
        return httpx.Response(200, json=[])

    transport, calls = _ha_mock(post)
    client = RestHomeAssistantClient("http://supervisor/core/api", token="tok", transport=transport)
    ok, err = asyncio.run(client.send_notification(
        domain="notify", service="galaxy_watch5_fhyw", title="T", message="M",
    ))
    assert ok is False
    assert len(calls) == 1, "must not retry through alternative actions"
    assert "HTTP 500" in err
    assert "notify.galaxy_watch5_fhyw" in err
    assert "mobile_app" in err
    assert "'unknown'" in err


def test_service_400_is_not_retried_through_send_message():
    transport, calls = _ha_mock(lambda r: httpx.Response(400, text="400: Bad Request"), states=[])
    client = RestHomeAssistantClient("http://supervisor/core/api", token="tok", transport=transport)
    ok, err = asyncio.run(client.send_notification(
        domain="notify", service="mobile_app_old_phone", title=None, message="M",
    ))
    assert ok is False
    assert len(calls) == 1
    assert "HTTP 400" in err and "Sync Services" in err


def test_blocked_actions_never_reach_home_assistant():
    transport, calls = _ha_mock(lambda r: httpx.Response(200, json=[]))
    client = RestHomeAssistantClient("http://supervisor/core/api", token="tok", transport=transport)
    for svc in ("dismiss", "dismiss_all"):
        ok, err = asyncio.run(client.send_notification(
            domain="persistent_notification", service=svc, title=None, message="M",
        ))
        assert ok is False and "Unsupported route" in err
    ok, err = asyncio.run(client.send_notification(domain="notify", service="send_message", title=None, message="M"))
    assert ok is False
    assert calls == []


def test_timeout_is_not_resent():
    def post(request):
        raise httpx.ReadTimeout("slow", request=request)

    transport, calls = _ha_mock(post)
    client = RestHomeAssistantClient("http://supervisor/core/api", token="tok", transport=transport)
    ok, err = asyncio.run(client.send_notification(
        domain="notify", service="mobile_app_galaxy_watch5_fhyw", title=None, message="M",
    ))
    assert ok is False
    assert len(calls) == 1
    assert "not resent" in err
