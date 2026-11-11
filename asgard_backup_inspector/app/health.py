"""Freshness evaluation. Pure functions, no I/O.

The verdict describes *metadata*: "a recent backup is listed". It never claims
that a backup can be restored.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .models import ApiStatus, BackupSummary, Freshness, GoogleDriveSummary, HealthSummary


def evaluate(
    backups: Optional[list[BackupSummary]],
    *,
    now: datetime,
    stale_threshold_hours: int,
    api_status: ApiStatus,
    supervisor_days_until_stale: Optional[int] = None,
    extra_warnings: Optional[list[str]] = None,
    local_count: Optional[int] = None,
    remote_count: Optional[int] = None,
    both_count: Optional[int] = None,
    pending_count: Optional[int] = None,
    local_only_count: Optional[int] = None,
    remote_only_count: Optional[int] = None,
    cloud_freshness: Optional[Freshness] = None,
    offsite_coverage: Optional[str] = None,
    full_backup_coverage: Optional[str] = None,
    google_drive: Optional[GoogleDriveSummary] = None,
) -> HealthSummary:
    """Build a HealthSummary.

    ``backups is None`` means "we have no data at all" (e.g. first fetch
    failed), which is different from an empty list ("API says zero backups").
    """
    warnings = list(extra_warnings or [])
    items = backups or []

    known_sizes = [b.size_bytes for b in items if b.size_bytes is not None]
    unknown_size_count = len(items) - len(known_sizes)
    dated = [b.created_utc for b in items if b.created_utc is not None]
    unknown_date_count = len(items) - len(dated)
    full_count = sum(1 for b in items if b.backup_type == "full")
    partial_count = sum(1 for b in items if b.backup_type == "partial")
    unknown_type_count = sum(1 for b in items if b.backup_type not in ("full", "partial"))
    full_bytes = sum(b.size_bytes for b in items if b.backup_type == "full" and b.size_bytes is not None)
    partial_bytes = sum(b.size_bytes for b in items if b.backup_type == "partial" and b.size_bytes is not None)
    unknown_type_bytes = sum(b.size_bytes for b in items if b.backup_type not in ("full", "partial") and b.size_bytes is not None)

    newest = max(dated) if dated else None
    age_seconds: Optional[int] = None
    if newest is not None:
        age_seconds = max(0, int((now - newest).total_seconds()))
        if newest > now:
            warnings.append("The newest backup has a date in the future; check the system clock.")

    if backups is None:
        freshness = Freshness.UNKNOWN
    elif not items:
        freshness = Freshness.NO_BACKUPS
    elif age_seconds is None:
        freshness = Freshness.UNKNOWN
        warnings.append("No backup has a readable creation date, so freshness cannot be judged.")
    elif age_seconds > stale_threshold_hours * 3600:
        freshness = Freshness.STALE
    else:
        freshness = Freshness.FRESH

    if unknown_size_count:
        warnings.append(
            f"{unknown_size_count} backup(s) report no size; the storage total only includes known sizes."
        )
    if unknown_date_count and freshness is not Freshness.UNKNOWN:
        warnings.append(f"{unknown_date_count} backup(s) have no readable creation date.")

    loc_cnt = len(items) if local_count is None else local_count
    rem_cnt = 0 if remote_count is None else remote_count
    bth_cnt = 0 if both_count is None else both_count
    pnd_cnt = 0 if pending_count is None else pending_count
    loc_only = loc_cnt if local_only_count is None else local_only_count
    rem_only = 0 if remote_only_count is None else remote_only_count

    c_fresh = Freshness.UNKNOWN if cloud_freshness is None else cloud_freshness
    off_cov = "unknown" if offsite_coverage is None else offsite_coverage
    if full_backup_coverage is not None:
        full_cov = full_backup_coverage
    else:
        full_dated = [b.created_utc for b in items if b.backup_type == "full" and b.created_utc is not None]
        if not full_dated:
            if unknown_type_count > 0:
                full_cov = "unverified"
            elif len(items) == 0:
                full_cov = "unknown"
            else:
                full_cov = "not_detected"
        else:
            newest_full = max(full_dated)
            full_age = max(0, int((now - newest_full).total_seconds()))
            full_cov = "present" if full_age <= stale_threshold_hours * 3600 else "stale"

    return HealthSummary(
        freshness=freshness,
        api_status=api_status,
        total_count=len(items),
        full_backup_count=full_count,
        partial_backup_count=partial_count,
        unknown_type_count=unknown_type_count,
        full_backup_bytes=full_bytes,
        partial_backup_bytes=partial_bytes,
        unknown_type_bytes=unknown_type_bytes,
        known_size_total_bytes=sum(known_sizes),
        unknown_size_count=unknown_size_count,
        unknown_date_count=unknown_date_count,
        newest_backup_utc=newest,
        newest_backup_age_seconds=age_seconds,
        stale_threshold_hours=stale_threshold_hours,
        supervisor_days_until_stale=supervisor_days_until_stale,
        warnings=warnings,
        local_count=loc_cnt,
        remote_count=rem_cnt,
        both_count=bth_cnt,
        pending_count=pnd_cnt,
        local_only_count=loc_only,
        remote_only_count=rem_only,
        cloud_freshness=c_fresh,
        offsite_coverage=off_cov,
        full_backup_coverage=full_cov,
        google_drive=google_drive,
    )
