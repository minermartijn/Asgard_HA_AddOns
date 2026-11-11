"""Contract tests for the Supervisor adapter, driven by a mock transport.

Shapes follow https://developers.home-assistant.io/docs/api/supervisor/ (verified
2026-11). These tests do NOT prove behaviour against a real Supervisor.
"""

import asyncio

import httpx
import pytest

from app.models import ApiStatus
from app.sources import MAX_RESPONSE_BYTES, SourceError, SupervisorBackupSource

TOKEN = "synthetic-test-token"


def run(coro):
    return asyncio.run(coro)


def make_source(handler, token=TOKEN):
    seen = []

    def wrapped(request: httpx.Request):
        seen.append(request)
        return handler(request)

    return SupervisorBackupSource(token=token, transport=httpx.MockTransport(wrapped)), seen


def test_only_performs_get_backups_info(fixture_bytes):
    source, seen = make_source(lambda r: httpx.Response(200, content=fixture_bytes("backups_ok.json")))
    result = run(source.fetch())
    assert len(result.backups) == 3
    assert len(seen) == 1
    req = seen[0]
    assert req.method == "GET"
    assert req.url.path == "/backups/info"
    assert req.url.host == "supervisor"
    assert req.headers["Authorization"] == f"Bearer {TOKEN}"


def test_empty_list(fixture_bytes):
    source, _ = make_source(lambda r: httpx.Response(200, content=fixture_bytes("backups_empty.json")))
    assert run(source.fetch()).backups == []


@pytest.mark.parametrize(
    "status, expected",
    [
        (401, ApiStatus.UNAUTHORIZED),
        (403, ApiStatus.FORBIDDEN),
        (400, ApiStatus.UNAVAILABLE),  # Supervisor still starting
        (500, ApiStatus.UNAVAILABLE),
        (502, ApiStatus.UNAVAILABLE),
        (404, ApiStatus.MALFORMED),
        (302, ApiStatus.MALFORMED),
    ],
)
def test_status_mapping(status, expected, fixture_bytes):
    body = fixture_bytes("backups_unauthorized.json")
    source, _ = make_source(lambda r: httpx.Response(status, content=body))
    with pytest.raises(SourceError) as info:
        run(source.fetch())
    assert info.value.status is expected
    # Upstream error text and the token must never be echoed to the user.
    assert "Synthetic forbidden message" not in info.value.message
    assert TOKEN not in info.value.message


def test_error_envelope_with_200_is_malformed(fixture_bytes):
    source, _ = make_source(lambda r: httpx.Response(200, content=fixture_bytes("backups_unauthorized.json")))
    with pytest.raises(SourceError) as info:
        run(source.fetch())
    assert info.value.status is ApiStatus.MALFORMED
    assert "Synthetic forbidden message" not in info.value.message


def test_malformed_data(fixture_bytes):
    source, _ = make_source(lambda r: httpx.Response(200, content=fixture_bytes("backups_malformed.json")))
    with pytest.raises(SourceError) as info:
        run(source.fetch())
    assert info.value.status is ApiStatus.MALFORMED


def test_invalid_json():
    source, _ = make_source(lambda r: httpx.Response(200, content=b"<html>nope</html>"))
    with pytest.raises(SourceError) as info:
        run(source.fetch())
    assert info.value.status is ApiStatus.MALFORMED


def test_oversized_response_rejected():
    source, _ = make_source(lambda r: httpx.Response(200, content=b" " * (MAX_RESPONSE_BYTES + 1)))
    with pytest.raises(SourceError) as info:
        run(source.fetch())
    assert info.value.status is ApiStatus.MALFORMED


def test_timeout():
    def handler(request):
        raise httpx.ReadTimeout("synthetic", request=request)

    source, _ = make_source(handler)
    with pytest.raises(SourceError) as info:
        run(source.fetch())
    assert info.value.status is ApiStatus.UNAVAILABLE


def test_connection_error():
    def handler(request):
        raise httpx.ConnectError("synthetic", request=request)

    source, _ = make_source(handler)
    with pytest.raises(SourceError) as info:
        run(source.fetch())
    assert info.value.status is ApiStatus.UNAVAILABLE


def test_missing_token_makes_no_request():
    source, seen = make_source(lambda r: httpx.Response(200), token=None)
    with pytest.raises(SourceError) as info:
        run(source.fetch())
    assert info.value.status is ApiStatus.NOT_CONFIGURED
    assert seen == []
