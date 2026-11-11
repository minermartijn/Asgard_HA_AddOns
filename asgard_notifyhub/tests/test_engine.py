"""Tests for ASGARD NotifyHub routing engine and quiet-hours policy logic."""

import asyncio
from datetime import datetime, timezone
import pytest
from app.client import DemoHomeAssistantClient
from app.engine import RoutingEngine, evaluate_quiet_hours
from app.models import (
    DeliveryStatus,
    Priority,
    QuietPolicy,
    Recipient,
    RecipientGroup,
    Route,
    SendRequest,
    TargetType,
)
from app.storage import Storage


def test_evaluate_quiet_hours_same_day():
    policy = QuietPolicy(
        id="pol_1",
        target_id="rec_1",
        quiet_start="13:00",
        quiet_end="15:00",
        day_mask=[0, 1, 2, 3, 4, 5, 6],
        timezone="UTC",
        urgent_override=False,
    )
    # 14:00 UTC (in window)
    dt_in = datetime(2026, 11, 11, 14, 0, tzinfo=timezone.utc)
    in_quiet, reason = evaluate_quiet_hours(policy, Priority.NORMAL, now_utc=dt_in)
    assert in_quiet is True
    assert "Silenced by quiet hours" in reason

    # 16:00 UTC (out of window)
    dt_out = datetime(2026, 11, 11, 16, 0, tzinfo=timezone.utc)
    in_quiet, reason = evaluate_quiet_hours(policy, Priority.NORMAL, now_utc=dt_out)
    assert in_quiet is False


def test_evaluate_quiet_hours_cross_midnight():
    policy = QuietPolicy(
        id="pol_night",
        target_id="rec_1",
        quiet_start="22:00",
        quiet_end="07:00",
        day_mask=[0, 1, 2, 3, 4],  # Mon-Fri
        timezone="UTC",
        urgent_override=True,
    )
    # Wednesday 23:30 (weekday 2, in late-night quiet hours)
    dt_late = datetime(2026, 11, 11, 23, 30, tzinfo=timezone.utc)
    in_quiet, reason = evaluate_quiet_hours(policy, Priority.NORMAL, now_utc=dt_late)
    assert in_quiet is True

    # Urgent override permits dispatch
    in_quiet, reason = evaluate_quiet_hours(policy, Priority.URGENT, now_utc=dt_late)
    assert in_quiet is False
    assert "Urgent priority overrides" in reason

    # Thursday 05:30 (weekday 3, in morning quiet hours initiated Wednesday evening)
    dt_morn = datetime(2026, 11, 12, 5, 30, tzinfo=timezone.utc)
    in_quiet, reason = evaluate_quiet_hours(policy, Priority.NORMAL, now_utc=dt_morn)
    assert in_quiet is True

    # Thursday 10:00 (outside quiet hours)
    dt_day = datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)
    in_quiet, reason = evaluate_quiet_hours(policy, Priority.NORMAL, now_utc=dt_day)
    assert in_quiet is False


def test_evaluate_quiet_hours_disabled():
    policy = QuietPolicy(
        id="pol_disabled",
        target_id="rec_1",
        quiet_start="00:00",
        quiet_end="23:59",
        day_mask=[0, 1, 2, 3, 4, 5, 6],
        enabled=False,
    )
    dt = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
    in_quiet, reason = evaluate_quiet_hours(policy, Priority.NORMAL, now_utc=dt)
    assert in_quiet is False
    assert "disabled" in reason


def test_routing_engine_preview_and_execute(temp_db_path):
    storage = Storage(temp_db_path)
    client = DemoHomeAssistantClient()
    engine = RoutingEngine(storage=storage, ha_client=client)

    # Setup Recipient & Routes
    rec = Recipient(id="rec_1", name="Thor", timezone="UTC", enabled=True)
    storage.save_recipient(rec)

    storage.save_route(Route(
        id="rt_1",
        recipient_id="rec_1",
        name="Mobile",
        ha_domain="notify",
        ha_service="mobile_app_phone",
        priority_min=Priority.NORMAL,
        enabled=True,
    ))

    storage.save_route(Route(
        id="rt_2",
        recipient_id="rec_1",
        name="Urgent Siren",
        ha_domain="notify",
        ha_service="siren",
        priority_min=Priority.URGENT,
        enabled=True,
    ))

    # Send informational priority request: neither should qualify (rt_1 requires normal, rt_2 requires urgent)
    req_info = SendRequest(
        recipient_id="rec_1",
        priority=Priority.INFORMATIONAL,
        message="Minor log info",
    )
    prev_info = engine.preview(req_info)
    assert len(prev_info.items) == 2
    assert all(not item.will_send for item in prev_info.items)

    # Send normal priority request: rt_1 will send, rt_2 will not
    req_norm = SendRequest(
        recipient_id="rec_1",
        priority=Priority.NORMAL,
        message="Laundry finished",
    )
    prev_norm = engine.preview(req_norm)
    assert len(prev_norm.items) == 2
    assert prev_norm.items[0].will_send is True
    assert prev_norm.items[1].will_send is False

    # Execute normal dispatch
    records = asyncio.run(engine.execute(req_norm))
    submitted = [r for r in records if r.status == DeliveryStatus.SUBMITTED]
    assert len(submitted) == 1
    assert submitted[0].route_id == "rt_1"

    # Immediately preview again: should hit deduplication window
    prev_dedup = engine.preview(req_norm, dedup_window_seconds=120)
    assert prev_dedup.items[0].dedup_hit is True
    assert prev_dedup.items[0].will_send is False


def test_routing_engine_group_target(temp_db_path):
    storage = Storage(temp_db_path)
    client = DemoHomeAssistantClient()
    engine = RoutingEngine(storage=storage, ha_client=client)

    # Create 2 recipients
    storage.save_recipient(Recipient(id="rec_a", name="Alice", enabled=True))
    storage.save_recipient(Recipient(id="rec_b", name="Bob", enabled=True))

    storage.save_route(Route(id="rt_a", recipient_id="rec_a", name="A Route", ha_domain="notify", ha_service="alice"))
    storage.save_route(Route(id="rt_b", recipient_id="rec_b", name="B Route", ha_domain="notify", ha_service="bob"))

    # Group with both
    storage.save_group(RecipientGroup(id="grp_all", name="Everyone", recipient_ids=["rec_a", "rec_b"]))

    req = SendRequest(
        group_id="grp_all",
        priority=Priority.NORMAL,
        message="Group alert",
    )
    prev = engine.preview(req)
    assert len(prev.items) == 2
    assert all(item.will_send for item in prev.items)

    records = asyncio.run(engine.execute(req))
    assert len(records) == 2
    assert all(r.status == DeliveryStatus.SUBMITTED for r in records)
