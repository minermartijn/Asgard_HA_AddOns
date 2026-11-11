"""Tests for SQLite persistence layer in ASGARD NotifyHub."""

from datetime import datetime, timezone
import pytest
from app.models import (
    DeliveryRecord,
    DeliveryStatus,
    Priority,
    QuietPolicy,
    Recipient,
    RecipientGroup,
    Route,
    TargetType,
)
from app.storage import Storage


def test_storage_init_creates_tables(storage: Storage):
    recipients = storage.list_recipients()
    assert isinstance(recipients, list)
    groups = storage.list_groups()
    assert isinstance(groups, list)
    policies = storage.list_policies()
    assert isinstance(policies, list)


def test_recipient_and_route_crud(storage: Storage):
    rec = Recipient(id="rec_alpha", name="Alice", timezone="Europe/Paris", enabled=True)
    storage.save_recipient(rec)

    fetched = storage.get_recipient("rec_alpha")
    assert fetched is not None
    assert fetched.name == "Alice"
    assert fetched.timezone == "Europe/Paris"
    assert fetched.routes == []

    rt = Route(
        id="rt_alpha_1",
        recipient_id="rec_alpha",
        name="Phone",
        ha_domain="notify",
        ha_service="mobile_app_iphone",
        priority_min=Priority.NORMAL,
        enabled=True,
    )
    storage.save_route(rt)

    fetched_with_routes = storage.get_recipient("rec_alpha")
    assert len(fetched_with_routes.routes) == 1
    assert fetched_with_routes.routes[0].ha_service == "mobile_app_iphone"

    # Delete route
    assert storage.delete_route("rt_alpha_1") is True
    assert len(storage.get_recipient("rec_alpha").routes) == 0

    # Delete recipient
    assert storage.delete_recipient("rec_alpha") is True
    assert storage.get_recipient("rec_alpha") is None


def test_cascading_route_deletion(storage: Storage):
    rec = Recipient(id="rec_beta", name="Bob", timezone="UTC", enabled=True)
    storage.save_recipient(rec)
    storage.save_route(Route(
        id="rt_beta_1",
        recipient_id="rec_beta",
        name="Push",
        ha_domain="notify",
        ha_service="mobile_app_bob",
    ))
    assert len(storage.get_recipient("rec_beta").routes) == 1

    # Deleting recipient should delete routes
    storage.delete_recipient("rec_beta")
    assert storage.get_recipient("rec_beta") is None


def test_group_crud(storage: Storage):
    # Ensure recipients exist first
    storage.save_recipient(Recipient(id="rec_1", name="R1"))
    storage.save_recipient(Recipient(id="rec_2", name="R2"))

    grp = RecipientGroup(
        id="grp_1",
        name="Security Team",
        description="Alarm recipients",
        recipient_ids=["rec_1", "rec_2"],
    )
    storage.save_group(grp)

    groups = storage.list_groups()
    assert len(groups) == 1
    assert groups[0].name == "Security Team"
    assert groups[0].recipient_ids == ["rec_1", "rec_2"]

    assert storage.delete_group("grp_1") is True
    assert len(storage.list_groups()) == 0


def test_policy_crud(storage: Storage):
    pol = QuietPolicy(
        id="pol_1",
        target_id="rec_alpha",
        target_type=TargetType.RECIPIENT,
        quiet_start="23:00",
        quiet_end="07:00",
        day_mask=[0, 1, 2, 3, 4],
        timezone="Europe/Amsterdam",
        urgent_override=True,
    )
    storage.save_policy(pol)

    pols = storage.list_policies(target_id="rec_alpha")
    assert len(pols) == 1
    assert pols[0].quiet_start == "23:00"
    assert pols[0].urgent_override is True

    assert storage.delete_policy("pol_1") is True
    assert len(storage.list_policies(target_id="rec_alpha")) == 0


def test_history_and_stats(storage: Storage):
    rec1 = DeliveryRecord(
        id="h_1",
        idempotency_key="req_1",
        created_utc=datetime.now(timezone.utc),
        recipient_id="rec_1",
        recipient_name="Alice",
        route_id="rt_1",
        ha_service="notify.mobile_app",
        priority=Priority.NORMAL,
        status=DeliveryStatus.SUBMITTED,
    )
    rec2 = DeliveryRecord(
        id="h_2",
        idempotency_key="req_2",
        created_utc=datetime.now(timezone.utc),
        recipient_id="rec_1",
        recipient_name="Alice",
        route_id="rt_1",
        ha_service="notify.mobile_app",
        priority=Priority.INFORMATIONAL,
        status=DeliveryStatus.BLOCKED_QUIET_HOURS,
    )
    storage.record_delivery(rec1)
    storage.record_delivery(rec2)

    history = storage.list_history(limit=10)
    assert len(history) == 2
    assert history[0].id == "h_2"  # Newest first

    stats = storage.get_stats_24h()
    assert stats["submissions_24h"] == 1
    assert stats["blocked_quiet_hours_24h"] == 1


def test_is_recent_duplicate(storage: Storage):
    rec = DeliveryRecord(
        id="h_dup",
        idempotency_key="req_dup",
        created_utc=datetime.now(timezone.utc),
        recipient_id="rec_1",
        recipient_name="Alice",
        route_id="rt_1",
        ha_service="mobile_app",
        priority=Priority.NORMAL,
        status=DeliveryStatus.SUBMITTED,
        content_hash="hash_12345",
    )
    storage.record_delivery(rec)

    # Within 60 seconds, same content hash
    assert storage.is_recent_duplicate(content_hash="hash_12345", window_seconds=60) is True
    # Non-existent hash
    assert storage.is_recent_duplicate(content_hash="other_hash", window_seconds=60) is False


def test_purge_history(storage: Storage):
    old_time = datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc)
    rec = DeliveryRecord(
        id="h_old",
        idempotency_key="req_old",
        created_utc=old_time,
        recipient_id="rec_1",
        recipient_name="Alice",
        route_id="rt_1",
        ha_service="mobile_app",
        priority=Priority.NORMAL,
        status=DeliveryStatus.SUBMITTED,
    )
    storage.record_delivery(rec)
    assert len(storage.list_history()) == 1

    purged = storage.purge_history(older_than_days=30)
    assert purged == 1
    assert len(storage.list_history()) == 0
