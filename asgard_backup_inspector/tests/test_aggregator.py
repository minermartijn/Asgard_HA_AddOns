"""Unit tests for BackupAggregator (deduplication, multi-location, redundancy)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.aggregator import BackupAggregator
from app.models import (
    BackupSummary,
    Freshness,
    GoogleDriveBackupItem,
    GoogleDriveSummary,
    LocationCategory,
)


def test_aggregate_supervisor_only():
    now = datetime.now(timezone.utc)
    local_backups = [
        BackupSummary(
            id="loc1",
            name="Daily Core",
            created_utc=now - timedelta(hours=2),
            size_bytes=1000,
            backup_type="full",
            location=".local",
            locations=[".local"],
        ),
        BackupSummary(
            id="loc2",
            name="Before Update",
            created_utc=now - timedelta(hours=10),
            size_bytes=500,
            backup_type="partial",
            location=".local",
            locations=[".local"],
        ),
    ]

    res = BackupAggregator.aggregate(
        local_backups,
        gdrive_summary=None,
        gdrive_items=None,
        stale_threshold_hours=48,
        now=now,
    )

    assert res.total_count == 2
    assert res.local_count == 2
    assert res.remote_count == 0
    assert res.both_count == 0
    assert res.local_only_count == 2
    assert res.remote_only_count == 0
    assert res.known_size_total_bytes == 1500
    assert res.local_freshness == Freshness.FRESH
    assert res.cloud_freshness == Freshness.UNKNOWN
    assert res.offsite_coverage == "unknown"
    assert res.full_backup_coverage == "present"


def test_aggregate_merges_and_deduplicates_by_slug():
    now = datetime.now(timezone.utc)

    # Local backups: loc1 and loc2
    local_backups = [
        BackupSummary(
            id="slug_shared_001",
            name="Daily Core",
            created_utc=now - timedelta(hours=5),
            size_bytes=2000,
            backup_type="full",
            location=".local",
            locations=[".local"],
        ),
        BackupSummary(
            id="slug_local_only",
            name="Quick Local Partial",
            created_utc=now - timedelta(hours=1),
            size_bytes=400,
            backup_type="partial",
            location=".local",
            locations=[".local"],
        ),
    ]

    # Google Drive: slug_shared_001 (replicated) and slug_drive_only (cloud only)
    gdrive_items = [
        GoogleDriveBackupItem(
            slug="slug_shared_001",
            name="Daily Core",
            date_utc=now - timedelta(hours=5),
            state="Backed Up",
            size_bytes=2000,
            backup_type="full",
        ),
        GoogleDriveBackupItem(
            slug="slug_drive_only",
            name="Old Monthly Cloud",
            date_utc=now - timedelta(days=30),
            state="Drive Only",
            size_bytes=3500,
            backup_type="full",
        ),
    ]

    gdrive_summary = GoogleDriveSummary(
        enabled=True,
        available=True,
        state="backed_up",
        backups_in_google_drive=2,
        backups_in_home_assistant=1,
        freshness=Freshness.FRESH,
    )

    res = BackupAggregator.aggregate(
        local_backups,
        gdrive_summary=gdrive_summary,
        gdrive_items=gdrive_items,
        stale_threshold_hours=48,
        now=now,
    )

    # Total unique backups should be 3 (shared, local-only, drive-only)
    assert res.total_count == 3
    assert res.local_count == 2
    assert res.remote_count == 2
    assert res.both_count == 1
    assert res.local_only_count == 1
    assert res.remote_only_count == 1

    # Deduplicated size: 2000 (shared once) + 400 (local) + 3500 (drive) = 5900
    assert res.known_size_total_bytes == 5900

    # Coverage: some local backups are missing from cloud -> incomplete
    assert res.offsite_coverage == "incomplete"
    assert res.local_freshness == Freshness.FRESH
    assert res.cloud_freshness == Freshness.FRESH

    # Verify the merged item details
    shared_item = next(b for b in res.backups if b.id == "slug_shared_001")
    assert shared_item.location_category == LocationCategory.BOTH.value
    assert "Google Drive" in shared_item.locations
    assert ".local" in shared_item.locations
    assert shared_item.metadata_source == "supervisor+google_drive"
    assert shared_item.sync_state == "Backed Up"

    drive_item = next(b for b in res.backups if b.id == "slug_drive_only")
    assert drive_item.location_category == LocationCategory.GOOGLE_DRIVE.value
    assert drive_item.locations == ["Google Drive"]
    assert drive_item.sync_state == "Drive Only"

    local_item = next(b for b in res.backups if b.id == "slug_local_only")
    assert local_item.location_category == LocationCategory.LOCAL.value
    assert local_item.sync_state == "Local Only"


def test_aggregate_confirmed_offsite_coverage():
    now = datetime.now(timezone.utc)
    local_backups = [
        BackupSummary(
            id="b1",
            name="Daily Core",
            created_utc=now - timedelta(hours=2),
            size_bytes=1000,
            backup_type="full",
            location=".local",
            locations=[".local"],
        ),
    ]
    gdrive_items = [
        GoogleDriveBackupItem(
            slug="b1",
            name="Daily Core",
            date_utc=now - timedelta(hours=2),
            state="Backed Up",
            size_bytes=1000,
            backup_type="full",
        ),
    ]
    gdrive_summary = GoogleDriveSummary(
        enabled=True,
        available=True,
        state="backed_up",
        freshness=Freshness.FRESH,
    )

    res = BackupAggregator.aggregate(
        local_backups,
        gdrive_summary=gdrive_summary,
        gdrive_items=gdrive_items,
        stale_threshold_hours=48,
        now=now,
    )

    assert res.both_count == 1
    assert res.local_only_count == 0
    assert res.offsite_coverage == "confirmed"


def test_aggregate_does_not_merge_by_name_alone():
    now = datetime.now(timezone.utc)

    # Same name "Automatic Backup", but different slugs
    local_backups = [
        BackupSummary(
            id="slug_aaa",
            name="Automatic Backup",
            created_utc=now - timedelta(hours=2),
            size_bytes=1000,
            backup_type="full",
        ),
    ]
    gdrive_items = [
        GoogleDriveBackupItem(
            slug="slug_bbb",
            name="Automatic Backup",
            date_utc=now - timedelta(days=5),
            state="Drive Only",
            size_bytes=1000,
            backup_type="full",
        ),
    ]
    gdrive_summary = GoogleDriveSummary(enabled=True, available=True, state="backed_up")

    res = BackupAggregator.aggregate(
        local_backups,
        gdrive_summary=gdrive_summary,
        gdrive_items=gdrive_items,
        stale_threshold_hours=48,
        now=now,
    )

    # Must preserve 2 distinct records!
    assert res.total_count == 2
    assert {b.id for b in res.backups} == {"slug_aaa", "slug_bbb"}
    assert res.both_count == 0
    assert res.local_only_count == 1
    assert res.remote_only_count == 1


def test_aggregate_pending_upload():
    now = datetime.now(timezone.utc)
    local_backups = [
        BackupSummary(
            id="b_pending",
            name="New Core Backup",
            created_utc=now - timedelta(minutes=5),
            size_bytes=1500,
            backup_type="full",
        ),
    ]
    gdrive_items = [
        GoogleDriveBackupItem(
            slug="b_pending",
            name="New Core Backup",
            date_utc=now - timedelta(minutes=5),
            state="Pending",
            size_bytes=1500,
            backup_type="full",
        ),
    ]
    gdrive_summary = GoogleDriveSummary(enabled=True, available=True, state="waiting")

    res = BackupAggregator.aggregate(
        local_backups,
        gdrive_summary=gdrive_summary,
        gdrive_items=gdrive_items,
        stale_threshold_hours=48,
        now=now,
    )

    assert res.total_count == 1
    assert res.pending_count == 1
    item = res.backups[0]
    assert item.location_category == LocationCategory.PENDING.value
    assert item.sync_state == "Pending Upload"
    assert res.offsite_coverage == "incomplete"


def test_aggregate_type_breakdown_and_unverified_full_coverage():
    now = datetime.now(timezone.utc)
    # 1 partial local backup, 2 Drive-only backups with None/unspecified type
    local_backups = [
        BackupSummary(
            id="local01",
            name="Manual_Full_Backup_11.11.26",
            created_utc=now - timedelta(hours=2),
            size_bytes=4_000_000_000,
            backup_type="partial",  # Classified as partial by HA Supervisor
        ),
    ]
    gdrive_items = [
        GoogleDriveBackupItem(
            slug="drive01",
            name="Remote Backup 1",
            date_utc=now - timedelta(days=1),
            state="Drive Only",
            size_bytes=20_000_000_000,
            backup_type=None,  # Google Drive sensor omits type
        ),
        GoogleDriveBackupItem(
            slug="drive02",
            name="Remote Backup 2",
            date_utc=now - timedelta(days=2),
            state="Drive Only",
            size_bytes=23_000_000_000,
            backup_type=None,
        ),
    ]
    gdrive_summary = GoogleDriveSummary(enabled=True, available=True, state="backed_up")

    res = BackupAggregator.aggregate(
        local_backups,
        gdrive_summary=gdrive_summary,
        gdrive_items=gdrive_items,
        stale_threshold_hours=48,
        now=now,
    )

    assert res.total_count == 3
    assert res.full_count == 0
    assert res.partial_count == 1
    assert res.unknown_type_count == 2
    assert res.partial_backup_bytes == 4_000_000_000
    assert res.unknown_type_bytes == 43_000_000_000
    assert res.full_backup_bytes == 0
    assert res.known_size_total_bytes == 47_000_000_000

    # Because 2 backups have unclassified type in Google Drive, coverage should be "unverified" rather than "not_detected"
    assert res.full_backup_coverage == "unverified"


def test_aggregate_confirmed_only_partial_marks_not_detected():
    now = datetime.now(timezone.utc)
    local_backups = [
        BackupSummary(
            id="local01",
            name="Core Settings",
            created_utc=now - timedelta(hours=1),
            size_bytes=100_000,
            backup_type="partial",
        ),
    ]
    res = BackupAggregator.aggregate(
        local_backups,
        gdrive_summary=None,
        gdrive_items=[],
        stale_threshold_hours=48,
        now=now,
    )
    assert res.full_count == 0
    assert res.partial_count == 1
    assert res.unknown_type_count == 0
    # When all backups are confirmed partial and none are unclassified, coverage is "not_detected"
    assert res.full_backup_coverage == "not_detected"
