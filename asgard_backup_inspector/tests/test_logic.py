from datetime import datetime, timedelta, timezone

import pytest

from app.health import evaluate
from app.models import ApiStatus, BackupSummary, Freshness
from app.normalize import MalformedResponse, normalize_backup, parse_backups_info, parse_datetime

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def backup(hours_ago=None, size=1000, slug="fake"):
    created = NOW - timedelta(hours=hours_ago) if hours_ago is not None else None
    return BackupSummary(id=slug, created_utc=created, size_bytes=size)


# ---- normalizer -----------------------------------------------------------

def test_parse_ok_fixture(fixture_data):
    result = parse_backups_info(fixture_data("backups_ok.json")["data"])
    assert [b.id for b in result.backups] == ["fake0001", "fake0002", "fake0003"]
    assert result.days_until_stale == 3
    assert result.skipped == 0
    first, second, third = result.backups
    assert first.size_bytes == 1288490189
    assert first.location == ".local"
    assert first.locations == [".local"]
    assert second.created_utc == datetime(2026, 10, 8, 12, 30, tzinfo=timezone.utc)  # +02:00 -> UTC
    assert second.locations == [".local", "fake_nas"]
    assert third.size_bytes is None  # missing size stays unknown, not 0


def test_parse_partial_fixture_skips_unusable_records(fixture_data):
    result = parse_backups_info(fixture_data("backups_partial.json")["data"])
    assert [b.id for b in result.backups] == ["fake0101", "fake0102"]
    assert result.skipped == 2
    assert result.warnings
    naive = result.backups[1]
    assert naive.created_utc is None  # naive timestamp rejected, not guessed
    assert naive.size_bytes is None   # boolean size rejected


def test_parse_malformed_raises(fixture_data):
    with pytest.raises(MalformedResponse):
        parse_backups_info(fixture_data("backups_malformed.json")["data"])
    with pytest.raises(MalformedResponse):
        parse_backups_info(None)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ({"slug": "a", "size_bytes": 0}, 0),            # real zero is kept
        ({"slug": "a", "size": 1.0}, 1024 * 1024),      # MB fallback
        ({"slug": "a", "size_bytes": -5}, None),
        ({"slug": "a", "size_bytes": "12"}, None),
        ({"slug": "a"}, None),
        ({"slug": "a", "size_bytes": 10**13}, 10**13),  # giant but valid
    ],
)
def test_size_handling(raw, expected):
    assert normalize_backup(raw).size_bytes == expected


@pytest.mark.parametrize(
    "value, ok",
    [
        ("2026-10-01T09:30:00Z", True),
        ("2026-10-01T09:30:00.123456+00:00", True),
        ("2026-10-01T09:30:00", False),
        ("yesterday", False),
        (None, False),
        (12345, False),
    ],
)
def test_parse_datetime(value, ok):
    assert (parse_datetime(value) is not None) is ok


def test_record_without_slug_is_skipped():
    assert normalize_backup({"name": "x"}) is None
    assert normalize_backup({"slug": ""}) is None
    assert normalize_backup(["slug"]) is None


# ---- health evaluator: acceptance criteria from the App spec -------------

def test_no_backups_is_not_healthy():
    s = evaluate([], now=NOW, stale_threshold_hours=48, api_status=ApiStatus.OK)
    assert s.freshness is Freshness.NO_BACKUPS
    assert s.total_count == 0
    assert s.newest_backup_age_seconds is None


def test_five_days_old_with_two_day_threshold_is_stale():
    s = evaluate([backup(hours_ago=5 * 24)], now=NOW, stale_threshold_hours=48, api_status=ApiStatus.OK)
    assert s.freshness is Freshness.STALE
    assert s.newest_backup_age_seconds == 5 * 24 * 3600


def test_recent_backup_is_fresh_and_uses_newest():
    s = evaluate(
        [backup(hours_ago=100, slug="old"), backup(hours_ago=3, slug="new")],
        now=NOW, stale_threshold_hours=48, api_status=ApiStatus.OK,
    )
    assert s.freshness is Freshness.FRESH
    assert s.newest_backup_age_seconds == 3 * 3600


def test_missing_size_is_reported_as_known_total_only():
    s = evaluate(
        [backup(hours_ago=1, size=1000), backup(hours_ago=2, size=None)],
        now=NOW, stale_threshold_hours=48, api_status=ApiStatus.OK,
    )
    assert s.known_size_total_bytes == 1000
    assert s.unknown_size_count == 1
    assert any("known sizes" in w for w in s.warnings)


def test_no_data_at_all_is_unknown():
    s = evaluate(None, now=NOW, stale_threshold_hours=48, api_status=ApiStatus.FORBIDDEN)
    assert s.freshness is Freshness.UNKNOWN
    assert s.api_status is ApiStatus.FORBIDDEN


def test_backups_without_dates_are_unknown_not_fresh():
    s = evaluate([backup(hours_ago=None)], now=NOW, stale_threshold_hours=48, api_status=ApiStatus.OK)
    assert s.freshness is Freshness.UNKNOWN


def test_future_date_warns():
    s = evaluate([backup(hours_ago=-5)], now=NOW, stale_threshold_hours=48, api_status=ApiStatus.OK)
    assert s.freshness is Freshness.FRESH
    assert any("future" in w for w in s.warnings)


def test_threshold_boundary_is_inclusive_fresh():
    s = evaluate([backup(hours_ago=48)], now=NOW, stale_threshold_hours=48, api_status=ApiStatus.OK)
    assert s.freshness is Freshness.FRESH


def test_mixed_valid_and_missing_dates_warns():
    s = evaluate([backup(hours_ago=2), backup(hours_ago=None)], now=NOW, stale_threshold_hours=48, api_status=ApiStatus.OK)
    assert s.freshness is Freshness.FRESH
    assert s.unknown_date_count == 1
    assert any("no readable creation date" in w for w in s.warnings)


def test_full_and_partial_backup_counts():
    b_full = BackupSummary(id="b1", backup_type="full", size_bytes=100)
    b_part = BackupSummary(id="b2", backup_type="partial", size_bytes=50)
    b_unk = BackupSummary(id="b3", backup_type=None, size_bytes=20)
    s = evaluate([b_full, b_part, b_unk], now=NOW, stale_threshold_hours=48, api_status=ApiStatus.OK)
    assert s.total_count == 3
    assert s.full_backup_count == 1
    assert s.partial_backup_count == 1
