"""Multi-provider backup architecture for Home Assistant.

Supports:
1. SupervisorBackupProvider: Reads local Supervisor backups via GET /backups/info.
2. GoogleDriveBackupProvider: Reads Google Drive Backup sensor state and attributes
   via GET /core/api/states/{sensor_entity_id}.
3. Demo and Mock providers for testing and offline environments.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

import httpx

from .models import (
    Freshness,
    GoogleDriveBackupItem,
    GoogleDriveSummary,
)
from .normalize import MalformedResponse, ParseResult, parse_backups_info, parse_datetime
from .sources import BACKUPS_INFO_PATH, MAX_RESPONSE_BYTES, SourceError, _parse_envelope

logger = logging.getLogger(__name__)


def parse_size_to_bytes(val: Any) -> tuple[Optional[int], Optional[str]]:
    """Parse size representation into (size_bytes, size_string)."""
    if val is None:
        return None, None
    if isinstance(val, (int, float)) and not isinstance(val, bool) and val >= 0:
        return int(round(val)), None
    if isinstance(val, str):
        clean = val.strip()
        if not clean:
            return None, None
        m = re.match(r"^([\d\.]+)\s*([A-Za-z]+)?$", clean)
        if m:
            num = float(m.group(1))
            unit = (m.group(2) or "B").upper()
            multipliers = {
                "B": 1,
                "KB": 1024,
                "KIB": 1024,
                "MB": 1024**2,
                "MIB": 1024**2,
                "GB": 1024**3,
                "GIB": 1024**3,
                "TB": 1024**4,
                "TIB": 1024**4,
            }
            if unit in multipliers:
                return int(round(num * multipliers[unit])), clean
        return None, clean
    return None, None


class CloudBackupProvider(Protocol):
    enabled: bool

    async def fetch(
        self, stale_threshold_hours: int, now: Optional[datetime] = None
    ) -> tuple[GoogleDriveSummary, list[GoogleDriveBackupItem]]: ...


@dataclass
class GoogleDriveBackupProvider:
    token: Optional[str]
    core_api_url: str = "http://supervisor/core/api"
    sensor_entity_id: str = "sensor.backup_state"
    timeout_seconds: float = 10.0
    transport: Optional[httpx.AsyncBaseTransport] = None
    enabled: bool = True

    async def fetch(
        self, stale_threshold_hours: int, now: Optional[datetime] = None
    ) -> tuple[GoogleDriveSummary, list[GoogleDriveBackupItem]]:
        current_time = now or datetime.now(timezone.utc)
        if not self.enabled:
            return (
                GoogleDriveSummary(
                    enabled=False,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    error_message=None,
                ),
                [],
            )

        if not self.token:
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    error_message="No token available for Home Assistant Core API.",
                ),
                [],
            )

        url = f"{self.core_api_url.rstrip('/')}/states/{self.sensor_entity_id}"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
                follow_redirects=False,
            ) as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {self.token}"},
                )
        except httpx.TimeoutException:
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    error_message="Home Assistant Core API request timed out.",
                ),
                [],
            )
        except httpx.HTTPError:
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    error_message="Could not connect to Home Assistant Core API.",
                ),
                [],
            )

        if response.status_code == 404:
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    state="not_found",
                    error_message=f"Sensor entity '{self.sensor_entity_id}' not found in Home Assistant (add-on may not be installed or sensor disabled).",
                ),
                [],
            )
        if response.status_code == 401:
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    state="unauthorized",
                    error_message="Home Assistant Core API rejected token (401).",
                ),
                [],
            )
        if response.status_code == 403:
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    state="forbidden",
                    error_message="Access forbidden (403). Check that 'homeassistant_api: true' is configured in App config.yaml.",
                ),
                [],
            )
        if response.status_code != 200:
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    state=f"http_{response.status_code}",
                    error_message=f"Core API returned unexpected HTTP {response.status_code}.",
                ),
                [],
            )

        try:
            payload = json.loads(response.content)
        except (ValueError, UnicodeDecodeError):
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    state="malformed_json",
                    error_message="Core API response was not valid JSON.",
                ),
                [],
            )

        if not isinstance(payload, dict):
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    state="malformed_response",
                    error_message="Core API entity state was not a valid dictionary.",
                ),
                [],
            )

        raw_state = payload.get("state")
        state_str = str(raw_state) if raw_state is not None else "unknown"

        if state_str.lower() in ("unavailable", "unknown"):
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    state=state_str,
                    error_message=f"Google Drive backup sensor is '{state_str}'.",
                ),
                [],
            )

        attributes = payload.get("attributes")
        if not isinstance(attributes, dict):
            attributes = {}

        warnings: list[str] = []
        last_upload_utc = parse_datetime(attributes.get("last_uploaded") or attributes.get("last_upload"))
        last_backup_utc = parse_datetime(attributes.get("last_backup"))

        cloud_freshness = Freshness.UNKNOWN
        if last_upload_utc is not None:
            age_sec = max(0, int((current_time - last_upload_utc).total_seconds()))
            if age_sec > stale_threshold_hours * 3600:
                cloud_freshness = Freshness.STALE
            else:
                cloud_freshness = Freshness.FRESH
        elif state_str.lower() == "backed_up":
            cloud_freshness = Freshness.FRESH

        def _clean_str(val: Any) -> Optional[str]:
            return str(val).strip() if val is not None and str(val).strip() else None

        def _clean_int(val: Any) -> int:
            if isinstance(val, (int, float)) and not isinstance(val, bool) and val >= 0:
                return int(val)
            return 0

        gdrive_count = _clean_int(
            attributes.get("backups_in_google_drive")
            or attributes.get("snapshots_in_google_drive")
        )
        ha_count = _clean_int(
            attributes.get("backups_in_home_assistant")
            or attributes.get("snapshots_in_home_assistant")
        )

        items: list[GoogleDriveBackupItem] = []
        raw_backups = attributes.get("backups") or attributes.get("snapshots")
        if isinstance(raw_backups, list):
            for raw in raw_backups:
                if not isinstance(raw, dict):
                    continue
                slug = _clean_str(raw.get("slug"))
                if not slug:
                    continue
                name = _clean_str(raw.get("name"))
                date_utc = parse_datetime(raw.get("date"))
                item_state = _clean_str(raw.get("state")) or "Backed Up"
                size_bytes, size_str = parse_size_to_bytes(raw.get("size"))
                raw_b_type = _clean_str(raw.get("type"))
                b_type = raw_b_type.lower() if raw_b_type is not None else None
                prot = raw.get("protected")
                is_prot = prot if isinstance(prot, bool) else None

                items.append(
                    GoogleDriveBackupItem(
                        slug=slug,
                        name=name,
                        date_utc=date_utc,
                        state=item_state,
                        size_bytes=size_bytes,
                        size_str=size_str,
                        backup_type=b_type,
                        protected=is_prot,
                    )
                )
        else:
            warnings.append(
                "Individual backup items are not published in sensor attributes (aggregate counts are used)."
            )

        summary = GoogleDriveSummary(
            enabled=True,
            available=True,
            sensor_entity_id=self.sensor_entity_id,
            state=state_str,
            backups_in_google_drive=gdrive_count or len([i for i in items if "Drive" in i.state or i.state == "Backed Up"]),
            backups_in_home_assistant=ha_count or len([i for i in items if "HA" in i.state or i.state == "Backed Up"]),
            size_in_google_drive=_clean_str(attributes.get("size_in_google_drive")),
            size_in_home_assistant=_clean_str(attributes.get("size_in_home_assistant")),
            free_space_in_google_drive=_clean_str(attributes.get("free_space_in_google_drive")),
            last_backup_utc=last_backup_utc,
            last_uploaded_utc=last_upload_utc,
            freshness=cloud_freshness,
            warnings=warnings,
        )
        return summary, items


@dataclass
class DemoGoogleDriveProvider:
    enabled: bool = True
    sensor_entity_id: str = "sensor.backup_state"

    async def fetch(
        self, stale_threshold_hours: int, now: Optional[datetime] = None
    ) -> tuple[GoogleDriveSummary, list[GoogleDriveBackupItem]]:
        if not self.enabled:
            return (
                GoogleDriveSummary(
                    enabled=False,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                ),
                [],
            )
        current = now or datetime.now(timezone.utc)
        last_upload = current - timedelta(hours=6)

        items = [
            # Matches demo0001 (Both)
            GoogleDriveBackupItem(
                slug="demo0001",
                name="Demo: automatic full backup",
                date_utc=current - timedelta(hours=9),
                state="Backed Up",
                size_bytes=1_288_490_189,
                size_str="1.2 GB",
                backup_type="full",
                protected=True,
            ),
            # Matches demo0002 (Both)
            GoogleDriveBackupItem(
                slug="demo0002",
                name="Demo: before core update",
                date_utc=current - timedelta(hours=30),
                state="Backed Up",
                size_bytes=412_000_000,
                size_str="392 MB",
                backup_type="partial",
                protected=True,
            ),
            # Remote-only backup 1 (Drive Only) - real Google Drive sensor omits type
            GoogleDriveBackupItem(
                slug="demo_drive_001",
                name="Demo: monthly archive 2026-10",
                date_utc=current - timedelta(days=25),
                state="Drive Only",
                size_bytes=1_250_000_000,
                size_str="1.16 GB",
                backup_type=None,
                protected=True,
            ),
            # Remote-only backup 2 (Drive Only) - real Google Drive sensor omits type
            GoogleDriveBackupItem(
                slug="demo_drive_002",
                name="Demo: monthly archive 2026-09",
                date_utc=current - timedelta(days=55),
                state="Drive Only",
                size_bytes=1_210_000_000,
                size_str="1.12 GB",
                backup_type=None,
                protected=True,
            ),
        ]

        summary = GoogleDriveSummary(
            enabled=True,
            available=True,
            sensor_entity_id=self.sensor_entity_id,
            state="backed_up",
            backups_in_google_drive=4,
            backups_in_home_assistant=2,
            size_in_google_drive="4.1 GB",
            size_in_home_assistant="1.6 GB",
            free_space_in_google_drive="11.2 GB",
            last_backup_utc=current - timedelta(hours=9),
            last_uploaded_utc=last_upload,
            freshness=Freshness.FRESH,
        )
        return summary, items


@dataclass
class MockGoogleDriveProvider:
    fixture_path: Path
    enabled: bool = True
    sensor_entity_id: str = "sensor.backup_state"

    async def fetch(
        self, stale_threshold_hours: int, now: Optional[datetime] = None
    ) -> tuple[GoogleDriveSummary, list[GoogleDriveBackupItem]]:
        if not self.enabled:
            return GoogleDriveSummary(enabled=False, available=False), []
        try:
            body = self.fixture_path.read_bytes()
            data = json.loads(body)
        except Exception as e:
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    error_message=f"Failed to read mock Google Drive fixture: {e}",
                ),
                [],
            )

        # Parse from dictionary representation
        current_time = now or datetime.now(timezone.utc)
        raw_state = data.get("state", "unknown")
        if raw_state in ("unavailable", "unknown"):
            return (
                GoogleDriveSummary(
                    enabled=True,
                    available=False,
                    sensor_entity_id=self.sensor_entity_id,
                    state=raw_state,
                    error_message=f"Google Drive sensor is {raw_state}.",
                ),
                [],
            )

        attrs = data.get("attributes", {})
        last_upload_utc = parse_datetime(attrs.get("last_uploaded") or attrs.get("last_upload"))
        last_backup_utc = parse_datetime(attrs.get("last_backup"))

        cloud_freshness = Freshness.UNKNOWN
        if last_upload_utc is not None:
            age_sec = max(0, int((current_time - last_upload_utc).total_seconds()))
            cloud_freshness = Freshness.STALE if age_sec > stale_threshold_hours * 3600 else Freshness.FRESH

        items: list[GoogleDriveBackupItem] = []
        for raw in attrs.get("backups", []):
            if not isinstance(raw, dict):
                continue
            slug = raw.get("slug")
            if not slug:
                continue
            s_bytes, s_str = parse_size_to_bytes(raw.get("size"))
            items.append(
                GoogleDriveBackupItem(
                    slug=slug,
                    name=raw.get("name"),
                    date_utc=parse_datetime(raw.get("date")),
                    state=raw.get("state", "Backed Up"),
                    size_bytes=s_bytes,
                    size_str=s_str,
                    backup_type=raw.get("type"),
                    protected=raw.get("protected"),
                )
            )

        summary = GoogleDriveSummary(
            enabled=True,
            available=True,
            sensor_entity_id=self.sensor_entity_id,
            state=raw_state,
            backups_in_google_drive=attrs.get("backups_in_google_drive", len(items)),
            backups_in_home_assistant=attrs.get("backups_in_home_assistant", 0),
            size_in_google_drive=attrs.get("size_in_google_drive"),
            size_in_home_assistant=attrs.get("size_in_home_assistant"),
            free_space_in_google_drive=attrs.get("free_space_in_google_drive"),
            last_backup_utc=last_backup_utc,
            last_uploaded_utc=last_upload_utc,
            freshness=cloud_freshness,
        )
        return summary, items
