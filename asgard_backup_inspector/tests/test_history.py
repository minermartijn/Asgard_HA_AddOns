"""Tests for HistoryStore and historical storage snapshots."""

from datetime import datetime, timedelta, timezone

from app.history import HistoryStore


def test_history_load_empty(tmp_path):
    store = HistoryStore(data_dir=tmp_path)
    entries = store.load()
    assert entries == []


def test_history_record_and_persist(tmp_path):
    store = HistoryStore(data_dir=tmp_path)
    now = datetime(2026, 11, 11, 10, 0, tzinfo=timezone.utc)

    # First record
    ok = store.record_snapshot(
        total_count=14,
        full_count=10,
        partial_count=4,
        known_size_bytes=14500000000,
        unknown_size_count=1,
        freshness="fresh",
        now=now,
    )
    assert ok is True
    assert len(store.get_entries()) == 1
    assert (tmp_path / "history.json").exists()

    # Re-loading from disk in a new store instance
    store2 = HistoryStore(data_dir=tmp_path)
    entries = store2.load()
    assert len(entries) == 1
    assert entries[0].total_count == 14
    assert entries[0].full_count == 10
    assert entries[0].partial_count == 4
    assert entries[0].known_size_bytes == 14500000000


def test_history_deduplication_within_interval(tmp_path):
    store = HistoryStore(data_dir=tmp_path)
    now = datetime(2026, 11, 11, 10, 0, tzinfo=timezone.utc)

    store.record_snapshot(
        total_count=14,
        full_count=10,
        partial_count=4,
        known_size_bytes=1000,
        unknown_size_count=0,
        freshness="fresh",
        now=now,
    )

    # Same data, only 10 minutes later -> should NOT record duplicate
    dupe = store.record_snapshot(
        total_count=14,
        full_count=10,
        partial_count=4,
        known_size_bytes=1000,
        unknown_size_count=0,
        freshness="fresh",
        now=now + timedelta(minutes=10),
    )
    assert dupe is False
    assert len(store.get_entries()) == 1

    # Data changed (count increased) -> SHOULD record immediately
    changed = store.record_snapshot(
        total_count=15,
        full_count=11,
        partial_count=4,
        known_size_bytes=1200,
        unknown_size_count=0,
        freshness="fresh",
        now=now + timedelta(minutes=15),
    )
    assert changed is True
    assert len(store.get_entries()) == 2


def test_history_corrupt_file_recovery(tmp_path):
    hist_file = tmp_path / "history.json"
    hist_file.write_text("invalid-json{", encoding="utf-8")

    store = HistoryStore(data_dir=tmp_path)
    entries = store.load()
    assert entries == []
    # Recording new snapshot recovers gracefully
    ok = store.record_snapshot(
        total_count=1,
        full_count=1,
        partial_count=0,
        known_size_bytes=100,
        unknown_size_count=0,
        freshness="fresh",
    )
    assert ok is True
    assert len(store.get_entries()) == 1
