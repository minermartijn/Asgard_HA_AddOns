"""Freshness evaluation. Pure functions, no I/O.

The verdict describes *metadata*: "a recent backup is listed". It never claims
that a backup can be restored.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .models import ApiStatus, BackupSummary, Freshness, HealthSummary


def evaluate(
    backups: Optional[list[BackupSummary]],
    *,
    now: datetime,
    stale_threshold_hours: int,
    api_status: ApiStatus,
    supervisor_days_until_stale: Optional[int] = None,
    extra_warnings: Optional[list[str]] = None,
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

    return HealthSummary(
        freshness=freshness,
        api_status=api_status,
        total_count=len(items),
        full_backup_count=full_count,
        partial_backup_count=partial_count,
        known_size_total_bytes=sum(known_sizes),
        unknown_size_count=unknown_size_count,
        unknown_date_count=unknown_date_count,
        newest_backup_utc=newest,
        newest_backup_age_seconds=age_seconds,
        stale_threshold_hours=stale_threshold_hours,
        supervisor_days_until_stale=supervisor_days_until_stale,
        warnings=warnings,
    )
