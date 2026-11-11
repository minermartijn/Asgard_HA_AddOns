"""Unit and contract tests for GoogleDriveBackupProvider."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.models import Freshness
from app.providers import (
    DemoGoogleDriveProvider,
    GoogleDriveBackupProvider,
    parse_size_to_bytes,
)


def test_parse_size_to_bytes():
    assert parse_size_to_bytes(None) == (None, None)
    assert parse_size_to_bytes(1024) == (1024, None)
    assert parse_size_to_bytes("1024") == (1024, "1024")
    assert parse_size_to_bytes("350 MB") == (350 * 1024 * 1024, "350 MB")
    assert parse_size_to_bytes("4.2 GB") == (round(4.2 * 1024 * 1024 * 1024), "4.2 GB")
    assert parse_size_to_bytes("invalid string") == (None, "invalid string")


def test_provider_disabled():
    provider = GoogleDriveBackupProvider(token="test-token", enabled=False)
    summary, items = asyncio.run(provider.fetch(stale_threshold_hours=48))
    assert not summary.enabled
    assert not summary.available
    assert items == []


def test_provider_no_token():
    provider = GoogleDriveBackupProvider(token=None, enabled=True)
    summary, items = asyncio.run(provider.fetch(stale_threshold_hours=48))
    assert summary.enabled
    assert not summary.available
    assert "No token" in (summary.error_message or "")
    assert items == []


def test_provider_sensor_404_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Entity not found."})

    transport = httpx.MockTransport(handler)
    provider = GoogleDriveBackupProvider(token="tok", transport=transport)
    summary, items = asyncio.run(provider.fetch(stale_threshold_hours=48))

    assert summary.enabled
    assert not summary.available
    assert summary.state == "not_found"
    assert "not found in Home Assistant" in (summary.error_message or "")
    assert items == []


def test_provider_sensor_403_forbidden():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Forbidden"})

    transport = httpx.MockTransport(handler)
    provider = GoogleDriveBackupProvider(token="tok", transport=transport)
    summary, items = asyncio.run(provider.fetch(stale_threshold_hours=48))

    assert not summary.available
    assert summary.state == "forbidden"
    assert "403" in (summary.error_message or "")


def test_provider_sensor_unavailable_state():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"entity_id": "sensor.backup_state", "state": "unavailable", "attributes": {}})

    transport = httpx.MockTransport(handler)
    provider = GoogleDriveBackupProvider(token="tok", transport=transport)
    summary, items = asyncio.run(provider.fetch(stale_threshold_hours=48))

    assert not summary.available
    assert summary.state == "unavailable"
    assert "unavailable" in (summary.error_message or "")
    assert items == []


def test_provider_sensor_success_with_backups():
    now = datetime.now(timezone.utc)
    upload_time = now - timedelta(hours=3)

    payload = {
        "entity_id": "sensor.backup_state",
        "state": "backed_up",
        "attributes": {
            "backups_in_google_drive": 15,
            "backups_in_home_assistant": 10,
            "size_in_google_drive": "4.2 GB",
            "size_in_home_assistant": "2.8 GB",
            "free_space_in_google_drive": "10.5 GB",
            "last_backup": (now - timedelta(hours=4)).isoformat(),
            "last_uploaded": upload_time.isoformat(),
            "backups": [
                {
                    "slug": "slug001",
                    "name": "Daily Core",
                    "date": (now - timedelta(hours=4)).isoformat(),
                    "state": "Backed Up",
                    "size": "350 MB",
                    "type": "full",
                    "protected": True,
                },
                {
                    "slug": "slug002",
                    "name": "Monthly Archive",
                    "date": (now - timedelta(days=20)).isoformat(),
                    "state": "Drive Only",
                    "size": "1.2 GB",
                    "type": "full",
                    "protected": True,
                },
            ],
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer tok"
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    provider = GoogleDriveBackupProvider(token="tok", transport=transport)
    summary, items = asyncio.run(provider.fetch(stale_threshold_hours=48, now=now))

    assert summary.enabled
    assert summary.available
    assert summary.state == "backed_up"
    assert summary.backups_in_google_drive == 15
    assert summary.backups_in_home_assistant == 10
    assert summary.size_in_google_drive == "4.2 GB"
    assert summary.free_space_in_google_drive == "10.5 GB"
    assert summary.freshness == Freshness.FRESH
    assert len(items) == 2

    assert items[0].slug == "slug001"
    assert items[0].state == "Backed Up"
    assert items[0].size_bytes == 350 * 1024 * 1024
    assert items[0].size_str == "350 MB"
    assert items[0].backup_type == "full"
    assert items[0].protected is True

    assert items[1].slug == "slug002"
    assert items[1].state == "Drive Only"


def test_provider_stale_upload():
    now = datetime.now(timezone.utc)
    upload_time = now - timedelta(hours=72)

    payload = {
        "entity_id": "sensor.backup_state",
        "state": "backed_up",
        "attributes": {
            "backups_in_google_drive": 5,
            "last_uploaded": upload_time.isoformat(),
            "backups": [],
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    provider = GoogleDriveBackupProvider(token="tok", transport=transport)
    summary, _ = asyncio.run(provider.fetch(stale_threshold_hours=48, now=now))

    assert summary.available
    assert summary.freshness == Freshness.STALE


def test_demo_gdrive_provider():
    provider = DemoGoogleDriveProvider(enabled=True)
    summary, items = asyncio.run(provider.fetch(stale_threshold_hours=48))
    assert summary.enabled
    assert summary.available
    assert summary.state == "backed_up"
    assert summary.freshness == Freshness.FRESH
    assert len(items) == 4
    drive_only = [i for i in items if i.state == "Drive Only"]
    assert len(drive_only) == 2
