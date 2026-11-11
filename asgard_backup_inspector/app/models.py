"""Normalized, read-only data transfer objects.

``None`` always means "unknown / not provided by the API". It is never
silently replaced by zero, ``False`` or "healthy".
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ApiStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"            # response parsed, but some records were unusable
    UNAUTHORIZED = "unauthorized"  # 401: token missing or rejected
    FORBIDDEN = "forbidden"        # 403: App lacks the Supervisor permission
    UNAVAILABLE = "unavailable"    # network error, timeout, 5xx, Supervisor starting
    MALFORMED = "malformed"        # unexpected response shape
    NOT_CONFIGURED = "not_configured"  # no Supervisor token (not running in HA)


class Freshness(str, Enum):
    FRESH = "fresh"            # newest backup is younger than the threshold
    STALE = "stale"            # newest backup is older than the threshold
    NO_BACKUPS = "no_backups"  # API answered, zero backups
    UNKNOWN = "unknown"        # no usable data (error, or no parsable dates)


class BackupSummary(BaseModel):
    id: str
    name: Optional[str] = None
    created_utc: Optional[datetime] = None
    size_bytes: Optional[int] = None
    backup_type: Optional[str] = None
    location: Optional[str] = None
    locations: list[str] = Field(default_factory=list)
    protected: Optional[bool] = None
    compressed: Optional[bool] = None
    metadata_source: str = "supervisor"


class HealthSummary(BaseModel):
    freshness: Freshness
    api_status: ApiStatus
    total_count: int
    full_backup_count: int = 0
    partial_backup_count: int = 0
    known_size_total_bytes: int
    unknown_size_count: int
    unknown_date_count: int
    newest_backup_utc: Optional[datetime] = None
    newest_backup_age_seconds: Optional[int] = None
    stale_threshold_hours: int
    supervisor_days_until_stale: Optional[int] = None
    warnings: list[str] = Field(default_factory=list)
    last_checked_utc: Optional[datetime] = None
    last_success_utc: Optional[datetime] = None
    showing_cached_data: bool = False
    demo_mode: bool = False
    error_message: Optional[str] = None
