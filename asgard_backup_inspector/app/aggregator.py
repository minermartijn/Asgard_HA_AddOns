"""Aggregation and deduplication logic across local and cloud backup providers.

Enforces least-privilege, read-only merging:
- Exact identifier match via slug.
- Never merges based only on similar names.
- Deduplicates storage metrics so replicated backups are not counted twice.
- Computes separate, uncoupled indicators for Local Freshness, Cloud Freshness,
  Off-site Coverage, and Full-Backup Coverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .models import (
    BackupSummary,
    Freshness,
    GoogleDriveBackupItem,
    GoogleDriveSummary,
    LocationCategory,
)


@dataclass
class AggregationResult:
    backups: list[BackupSummary]
    total_count: int
    local_count: int
    remote_count: int
    both_count: int
    pending_count: int
    local_only_count: int
    remote_only_count: int
    full_count: int
    partial_count: int
    unknown_type_count: int
    full_backup_bytes: int
    partial_backup_bytes: int
    unknown_type_bytes: int
    known_size_total_bytes: int
    unknown_size_count: int
    unknown_date_count: int
    newest_backup_utc: Optional[datetime]
    newest_backup_age_seconds: Optional[int]
    local_freshness: Freshness
    cloud_freshness: Freshness
    offsite_coverage: str
    full_backup_coverage: str
    warnings: list[str]


class BackupAggregator:
    @staticmethod
    def aggregate(
        local_backups: Optional[list[BackupSummary]],
        gdrive_summary: Optional[GoogleDriveSummary],
        gdrive_items: Optional[list[GoogleDriveBackupItem]],
        *,
        stale_threshold_hours: int,
        now: datetime,
    ) -> AggregationResult:
        warnings: list[str] = []
        locals_list = local_backups or []
        gdrive_items_list = gdrive_items or []
        cloud_active = gdrive_summary is not None and gdrive_summary.available

        local_by_slug = {b.id: b for b in locals_list}
        matched_slugs: set[str] = set()
        merged: list[BackupSummary] = []

        if cloud_active:
            for g_item in gdrive_items_list:
                slug = g_item.slug
                if slug in local_by_slug:
                    # Present in both local Supervisor and Google Drive sensor
                    local = local_by_slug[slug]
                    matched_slugs.add(slug)
                    state_norm = (g_item.state or "Backed Up").strip()

                    if state_norm.lower() in ("backed up", "backed_up", "synced"):
                        loc_cat = LocationCategory.BOTH.value
                        sync_st = "Backed Up"
                        locs = list(dict.fromkeys(local.locations + ["Google Drive"]))
                        meta_src = "supervisor+google_drive"
                    elif state_norm.lower() in ("pending", "waiting", "uploading"):
                        loc_cat = LocationCategory.PENDING.value
                        sync_st = "Pending Upload"
                        locs = local.locations
                        meta_src = "supervisor+google_drive"
                    elif state_norm.lower() in ("ha only", "ha_only"):
                        loc_cat = LocationCategory.LOCAL.value
                        sync_st = "Local Only"
                        locs = local.locations
                        meta_src = "supervisor+google_drive"
                    else:
                        loc_cat = LocationCategory.BOTH.value
                        sync_st = state_norm
                        locs = list(dict.fromkeys(local.locations + ["Google Drive"]))
                        meta_src = "supervisor+google_drive"

                    merged.append(
                        BackupSummary(
                            id=local.id,
                            name=local.name or g_item.name,
                            created_utc=local.created_utc or g_item.date_utc,
                            size_bytes=local.size_bytes or g_item.size_bytes,
                            backup_type=local.backup_type or g_item.backup_type,
                            location=local.location,
                            locations=locs,
                            protected=local.protected if local.protected is not None else g_item.protected,
                            compressed=local.compressed,
                            metadata_source=meta_src,
                            location_category=loc_cat,
                            sync_state=sync_st,
                            remote_size_bytes=g_item.size_bytes,
                        )
                    )
                else:
                    # Present only in Google Drive (Drive Only)
                    merged.append(
                        BackupSummary(
                            id=slug,
                            name=g_item.name,
                            created_utc=g_item.date_utc,
                            size_bytes=g_item.size_bytes,
                            backup_type=g_item.backup_type,
                            location="Google Drive",
                            locations=["Google Drive"],
                            protected=g_item.protected,
                            compressed=None,
                            metadata_source="google_drive",
                            location_category=LocationCategory.GOOGLE_DRIVE.value,
                            sync_state="Drive Only",
                            remote_size_bytes=g_item.size_bytes,
                        )
                    )

        # Append remaining local backups not matched with Google Drive items
        for local in locals_list:
            if local.id not in matched_slugs:
                sync_st = "Local Only" if cloud_active else None
                merged.append(
                    BackupSummary(
                        id=local.id,
                        name=local.name,
                        created_utc=local.created_utc,
                        size_bytes=local.size_bytes,
                        backup_type=local.backup_type,
                        location=local.location,
                        locations=local.locations or [".local"],
                        protected=local.protected,
                        compressed=local.compressed,
                        metadata_source=local.metadata_source,
                        location_category=LocationCategory.LOCAL.value,
                        sync_state=sync_st,
                        remote_size_bytes=None,
                    )
                )

        epoch = datetime.min.replace(tzinfo=timezone.utc)
        merged.sort(key=lambda b: b.created_utc or epoch, reverse=True)

        local_count = sum(
            1 for b in merged if b.location_category in (LocationCategory.LOCAL.value, LocationCategory.BOTH.value, LocationCategory.PENDING.value)
        )
        remote_count = sum(
            1 for b in merged if b.location_category in (LocationCategory.GOOGLE_DRIVE.value, LocationCategory.BOTH.value)
        )
        both_count = sum(1 for b in merged if b.location_category == LocationCategory.BOTH.value)
        pending_count = sum(1 for b in merged if b.location_category == LocationCategory.PENDING.value)
        local_only_count = sum(1 for b in merged if b.location_category == LocationCategory.LOCAL.value)
        remote_only_count = sum(1 for b in merged if b.location_category == LocationCategory.GOOGLE_DRIVE.value)

        full_count = sum(1 for b in merged if b.backup_type == "full")
        partial_count = sum(1 for b in merged if b.backup_type == "partial")
        unknown_type_count = sum(1 for b in merged if b.backup_type not in ("full", "partial"))

        full_backup_bytes = sum(b.size_bytes for b in merged if b.backup_type == "full" and b.size_bytes is not None)
        partial_backup_bytes = sum(b.size_bytes for b in merged if b.backup_type == "partial" and b.size_bytes is not None)
        unknown_type_bytes = sum(b.size_bytes for b in merged if b.backup_type not in ("full", "partial") and b.size_bytes is not None)

        known_sizes = [b.size_bytes for b in merged if b.size_bytes is not None]
        known_size_total_bytes = sum(known_sizes)
        unknown_size_count = len(merged) - len(known_sizes)

        dated = [b.created_utc for b in merged if b.created_utc is not None]
        unknown_date_count = len(merged) - len(dated)
        newest = max(dated) if dated else None
        age_seconds: Optional[int] = None
        if newest is not None:
            age_seconds = max(0, int((now - newest).total_seconds()))
            if newest > now:
                warnings.append("The newest backup has a date in the future; check the system clock.")

        # Local freshness
        local_dated = [
            b.created_utc
            for b in merged
            if b.created_utc is not None and b.location_category in (LocationCategory.LOCAL.value, LocationCategory.BOTH.value, LocationCategory.PENDING.value)
        ]
        if local_backups is None:
            local_freshness = Freshness.UNKNOWN
        elif not locals_list:
            local_freshness = Freshness.NO_BACKUPS
        elif not local_dated:
            local_freshness = Freshness.UNKNOWN
            warnings.append("No local backup has a readable creation date.")
        else:
            newest_local = max(local_dated)
            local_age = max(0, int((now - newest_local).total_seconds()))
            if local_age > stale_threshold_hours * 3600:
                local_freshness = Freshness.STALE
            else:
                local_freshness = Freshness.FRESH

        # Cloud freshness
        if gdrive_summary is None or not gdrive_summary.available:
            cloud_freshness = Freshness.UNKNOWN
        else:
            cloud_freshness = gdrive_summary.freshness

        # Offsite coverage
        if not cloud_active:
            offsite_coverage = "unknown"
        elif local_count == 0 and remote_count == 0:
            offsite_coverage = "unknown"
        elif both_count > 0 and local_only_count == 0 and pending_count == 0:
            offsite_coverage = "confirmed"
        elif (both_count > 0 or pending_count > 0) and (local_only_count > 0 or pending_count > 0):
            offsite_coverage = "incomplete"
        elif both_count == 0 and pending_count == 0 and local_count > 0:
            offsite_coverage = "none"
        else:
            offsite_coverage = "incomplete" if (local_only_count > 0 or pending_count > 0) else "confirmed"

        # Full backup coverage
        full_dated = [b.created_utc for b in merged if b.backup_type == "full" and b.created_utc is not None]
        if not full_dated:
            if unknown_type_count > 0:
                full_backup_coverage = "unverified"
            elif len(merged) == 0:
                full_backup_coverage = "unknown"
            else:
                full_backup_coverage = "not_detected"
        else:
            newest_full = max(full_dated)
            full_age = max(0, int((now - newest_full).total_seconds()))
            if full_age <= stale_threshold_hours * 3600:
                full_backup_coverage = "present"
            else:
                full_backup_coverage = "stale"

        if unknown_size_count:
            warnings.append(
                f"{unknown_size_count} backup(s) report no size; the storage total only includes known sizes."
            )
        if unknown_date_count and local_freshness is not Freshness.UNKNOWN:
            warnings.append(f"{unknown_date_count} backup(s) have no readable creation date.")

        if gdrive_summary and gdrive_summary.warnings:
            warnings.extend(gdrive_summary.warnings)

        return AggregationResult(
            backups=merged,
            total_count=len(merged),
            local_count=local_count,
            remote_count=remote_count,
            both_count=both_count,
            pending_count=pending_count,
            local_only_count=local_only_count,
            remote_only_count=remote_only_count,
            full_count=full_count,
            partial_count=partial_count,
            unknown_type_count=unknown_type_count,
            full_backup_bytes=full_backup_bytes,
            partial_backup_bytes=partial_backup_bytes,
            unknown_type_bytes=unknown_type_bytes,
            known_size_total_bytes=known_size_total_bytes,
            unknown_size_count=unknown_size_count,
            unknown_date_count=unknown_date_count,
            newest_backup_utc=newest,
            newest_backup_age_seconds=age_seconds,
            local_freshness=local_freshness,
            cloud_freshness=cloud_freshness,
            offsite_coverage=offsite_coverage,
            full_backup_coverage=full_backup_coverage,
            warnings=warnings,
        )
