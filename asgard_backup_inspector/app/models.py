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


class LocationCategory(str, Enum):
    LOCAL = "local"
    GOOGLE_DRIVE = "google_drive"
    BOTH = "both"
    PENDING = "pending"
    UNKNOWN = "unknown"


class OffsiteCoverage(str, Enum):
    CONFIRMED = "confirmed"      # all local backups (or latest) verified offsite
    INCOMPLETE = "incomplete"    # some backups missing from cloud
    NONE = "none"                # no offsite copies detected
    UNKNOWN = "unknown"          # cloud sensor disabled or unavailable


class FullBackupCoverage(str, Enum):
    PRESENT = "present"          # fresh full backup exists
    STALE = "stale"              # full backup exists but is older than threshold
    NOT_DETECTED = "not_detected" # only confirmed partial backups found
    UNVERIFIED = "unverified"    # no confirmed full backup, but unclassified backups exist
    UNKNOWN = "unknown"


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
    location_category: str = "local"  # "local", "google_drive", "both", "pending", "unknown"
    sync_state: Optional[str] = None  # e.g. "Backed Up", "Drive Only", "HA Only", "Pending"
    remote_size_bytes: Optional[int] = None


class GoogleDriveBackupItem(BaseModel):
    slug: str
    name: Optional[str] = None
    date_utc: Optional[datetime] = None
    state: str = "Backed Up"
    size_bytes: Optional[int] = None
    size_str: Optional[str] = None
    backup_type: Optional[str] = None
    protected: Optional[bool] = None


class GoogleDriveSummary(BaseModel):
    enabled: bool = True
    available: bool = False
    sensor_entity_id: str = "sensor.backup_state"
    state: Optional[str] = None
    backups_in_google_drive: int = 0
    backups_in_home_assistant: int = 0
    size_in_google_drive: Optional[str] = None
    size_in_home_assistant: Optional[str] = None
    free_space_in_google_drive: Optional[str] = None
    last_backup_utc: Optional[datetime] = None
    last_uploaded_utc: Optional[datetime] = None
    freshness: Freshness = Freshness.UNKNOWN
    error_message: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


class HealthSummary(BaseModel):
    freshness: Freshness
    api_status: ApiStatus
    total_count: int
    full_backup_count: int = 0
    partial_backup_count: int = 0
    unknown_type_count: int = 0
    full_backup_bytes: int = 0
    partial_backup_bytes: int = 0
    unknown_type_bytes: int = 0
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

    # Multi-location & Redundancy metrics
    local_count: int = 0
    remote_count: int = 0
    both_count: int = 0
    pending_count: int = 0
    local_only_count: int = 0
    remote_only_count: int = 0
    cloud_freshness: Freshness = Freshness.UNKNOWN
    offsite_coverage: str = "unknown"
    full_backup_coverage: str = "unknown"
    google_drive: Optional[GoogleDriveSummary] = None
