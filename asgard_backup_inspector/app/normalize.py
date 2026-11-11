"""Turn raw Supervisor ``/backups/info`` data into normalized records.

Transport-independent: accepts the already-unwrapped ``data`` dict of the
Supervisor envelope. Reference (verified 2026-11):
https://developers.home-assistant.io/docs/api/supervisor/models (Backup model)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .models import BackupSummary


class MalformedResponse(ValueError):
    """The response does not have the documented top-level shape."""


@dataclass
class ParseResult:
    backups: list[BackupSummary]
    skipped: int = 0
    days_until_stale: Optional[int] = None
    warnings: list[str] = field(default_factory=list)


def _opt_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value != "" else None


def _opt_bool(value: Any) -> Optional[bool]:
    return value if isinstance(value, bool) else None


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp into an aware UTC datetime.

    Naive timestamps are rejected (returned as ``None``) instead of guessing a
    timezone, because a wrong guess would produce a wrong freshness verdict.
    """
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def parse_size_bytes(raw: dict[str, Any]) -> Optional[int]:
    """Prefer exact ``size_bytes``; fall back to ``size`` (MB, float).

    Booleans, negatives and non-numbers are treated as unknown, never as 0.
    """
    exact = raw.get("size_bytes")
    if isinstance(exact, int) and not isinstance(exact, bool) and exact >= 0:
        return exact
    megabytes = raw.get("size")
    if isinstance(megabytes, (int, float)) and not isinstance(megabytes, bool) and megabytes >= 0:
        return int(round(megabytes * 1024 * 1024))
    return None


def normalize_backup(raw: Any) -> Optional[BackupSummary]:
    """Return a normalized record, or ``None`` when no usable identifier exists."""
    if not isinstance(raw, dict):
        return None
    slug = _opt_str(raw.get("slug"))
    if slug is None:
        return None
    raw_locations = raw.get("locations")
    locations: list[str] = []
    if isinstance(raw_locations, list):
        for loc in raw_locations:
            # ``null`` is the documented name for the local backup folder.
            if loc is None:
                locations.append(".local")
            elif isinstance(loc, str):
                locations.append(loc)
    location = raw.get("location")
    return BackupSummary(
        id=slug,
        name=_opt_str(raw.get("name")),
        created_utc=parse_datetime(raw.get("date")),
        size_bytes=parse_size_bytes(raw),
        backup_type=_opt_str(raw.get("type")),
        location=".local" if location is None and "location" in raw else _opt_str(location),
        locations=locations,
        protected=_opt_bool(raw.get("protected")),
        compressed=_opt_bool(raw.get("compressed")),
    )


def parse_backups_info(data: Any) -> ParseResult:
    if not isinstance(data, dict) or not isinstance(data.get("backups"), list):
        raise MalformedResponse("response data has no 'backups' list")
    backups: list[BackupSummary] = []
    skipped = 0
    for raw in data["backups"]:
        record = normalize_backup(raw)
        if record is None:
            skipped += 1
        else:
            backups.append(record)
    days = data.get("days_until_stale")
    days_until_stale = days if isinstance(days, int) and not isinstance(days, bool) and days > 0 else None
    warnings = []
    if skipped:
        warnings.append(f"{skipped} backup record(s) were skipped because they had no usable identifier.")
    return ParseResult(backups=backups, skipped=skipped, days_until_stale=days_until_stale, warnings=warnings)
