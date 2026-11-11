"""Backup metadata sources.

``SupervisorBackupSource`` performs exactly one kind of request:
``GET http://supervisor/backups/info``. It has no code path that creates,
deletes, restores or downloads backups.

Permission note: with ``hassio_api: true`` the Supervisor's ``default`` role
allows every path ending in ``/info`` (see supervisor/api/middleware/security.py,
pattern ``^/.+/info$``), which includes ``/backups/info``. The broader
``backup`` role would also allow create/restore/delete and is deliberately not
requested. A 403 is reported to the user as a permission problem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

import httpx

from .models import ApiStatus
from .normalize import MalformedResponse, ParseResult, parse_backups_info

BACKUPS_INFO_PATH = "/backups/info"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class SourceError(Exception):
    """A fetch failed. ``message`` is safe to show to an Ingress user."""

    def __init__(self, status: ApiStatus, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class BackupSource(Protocol):
    demo: bool

    async def fetch(self) -> ParseResult: ...


@dataclass
class SupervisorBackupSource:
    token: Optional[str]
    base_url: str = "http://supervisor"
    timeout_seconds: float = 10.0
    transport: Optional[httpx.AsyncBaseTransport] = None  # injected by tests
    demo: bool = False

    async def fetch(self) -> ParseResult:
        if not self.token:
            raise SourceError(
                ApiStatus.NOT_CONFIGURED,
                "No Supervisor token is available. The App must run inside Home Assistant.",
            )
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
                follow_redirects=False,
            ) as client:
                response = await client.get(
                    BACKUPS_INFO_PATH,
                    headers={"Authorization": f"Bearer {self.token}"},
                )
        except httpx.TimeoutException:
            raise SourceError(ApiStatus.UNAVAILABLE, "The Supervisor did not answer in time.") from None
        except httpx.HTTPError:
            raise SourceError(ApiStatus.UNAVAILABLE, "The Supervisor could not be reached.") from None

        if response.status_code == 401:
            raise SourceError(ApiStatus.UNAUTHORIZED, "The Supervisor rejected the App token (401).")
        if response.status_code == 403:
            raise SourceError(
                ApiStatus.FORBIDDEN,
                "The App is not allowed to read backup information (403). "
                "Check that the App is up to date; it requires 'hassio_api'.",
            )
        if response.status_code >= 500 or response.status_code == 400:
            # 400 is also what the Supervisor returns while it is starting up.
            raise SourceError(
                ApiStatus.UNAVAILABLE,
                f"The Supervisor returned an error (HTTP {response.status_code}).",
            )
        if response.status_code != 200:
            raise SourceError(ApiStatus.MALFORMED, f"Unexpected Supervisor response (HTTP {response.status_code}).")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise SourceError(ApiStatus.MALFORMED, "The Supervisor response was unexpectedly large.")

        return _parse_envelope(response.content)


def _parse_envelope(body: bytes) -> ParseResult:
    try:
        payload: Any = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise SourceError(ApiStatus.MALFORMED, "The Supervisor response was not valid JSON.") from None
    if not isinstance(payload, dict) or payload.get("result") != "ok":
        # Do not echo the upstream message: it is not needed and may contain details.
        raise SourceError(ApiStatus.MALFORMED, "The Supervisor reported an error or an unexpected format.")
    try:
        return parse_backups_info(payload.get("data"))
    except MalformedResponse:
        raise SourceError(ApiStatus.MALFORMED, "The Supervisor response did not contain a backup list.") from None


@dataclass
class DemoBackupSource:
    """Synthetic backups with dates relative to *now*, for the ``demo_mode`` option.

    All names and slugs are invented. Nothing is read from the real system.
    """

    demo: bool = True

    async def fetch(self) -> ParseResult:
        now = datetime.now(timezone.utc)

        def item(slug: str, name: str, hours_ago: float, kind: str, size: Optional[int], **extra: Any) -> dict:
            record = {
                "slug": slug,
                "name": name,
                "date": (now - timedelta(hours=hours_ago)).isoformat(),
                "type": kind,
                "location": None,
                "locations": [None],
                "protected": True,
                "compressed": True,
            }
            if size is not None:
                record["size_bytes"] = size
            record.update(extra)
            return record

        envelope = {
            "result": "ok",
            "data": {
                "days_until_stale": 3,
                "backups": [
                    item("demo0001", "Demo: automatic full backup", 9, "full", 1_288_490_189),
                    item("demo0002", "Demo: before core update", 30, "partial", 412_000_000),
                    item("demo0003", "Demo: automatic full backup", 33, "full", 1_270_000_000,
                         location="demo_nas", locations=[None, "demo_nas"]),
                    item("demo0004", "Demo: imported backup without size", 200, "full", None),
                ],
            },
        }
        return _parse_envelope(json.dumps(envelope).encode())


@dataclass
class MockBackupSource:
    """Serves a synthetic Supervisor envelope from a JSON file (demo / development)."""

    fixture_path: Path
    demo: bool = True

    async def fetch(self) -> ParseResult:
        try:
            body = self.fixture_path.read_bytes()
        except OSError:
            raise SourceError(ApiStatus.UNAVAILABLE, "Demo data file is missing.") from None
        return _parse_envelope(body)
