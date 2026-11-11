"""Tests for ASGARD NotifyHub domain models and validation."""

from datetime import datetime, timezone
import pytest
from app.models import (
    DeliveryRecord,
    DeliveryStatus,
    PreviewItem,
    Priority,
    QuietPolicy,
    Recipient,
    RecipientGroup,
    Route,
    SendRequest,
    TargetType,
)


def test_priority_ordering():
    assert Priority.INFORMATIONAL.level < Priority.NORMAL.level
    assert Priority.NORMAL.level < Priority.URGENT.level
    assert Priority.INFORMATIONAL < Priority.NORMAL
    assert Priority.NORMAL < Priority.URGENT
    assert not (Priority.URGENT < Priority.NORMAL)


def test_delivery_status_values():
    assert DeliveryStatus.SUBMITTED.value == "submitted"
    assert DeliveryStatus.BLOCKED_QUIET_HOURS.value == "blocked_quiet_hours"
    assert DeliveryStatus.SUPPRESSED_DUPLICATE.value == "suppressed_duplicate"
    assert DeliveryStatus.FAILED.value == "failed"


def test_recipient_model():
    rec = Recipient(id="rec_1", name="Martijn", timezone="Europe/Amsterdam", enabled=True)
    assert rec.id == "rec_1"
    assert rec.name == "Martijn"
    assert rec.timezone == "Europe/Amsterdam"
    assert rec.enabled is True
    assert rec.routes == []


def test_route_model():
    rt = Route(
        id="rt_1",
        recipient_id="rec_1",
        name="Mobile App",
        ha_domain="notify",
        ha_service="mobile_app_pixel",
        priority_min=Priority.NORMAL,
        enabled=True,
    )
    assert rt.full_action == "notify.mobile_app_pixel"
    assert rt.priority_min == Priority.NORMAL


def test_recipient_group_model():
    grp = RecipientGroup(
        id="grp_1",
        name="Admins",
        description="Household administrators",
        recipient_ids=["rec_1", "rec_2"],
    )
    assert grp.name == "Admins"
    assert len(grp.recipient_ids) == 2


def test_quiet_policy_model():
    pol = QuietPolicy(
        id="pol_1",
        target_id="rec_1",
        target_type=TargetType.RECIPIENT,
        quiet_start="22:30",
        quiet_end="06:30",
        day_mask=[0, 1, 2, 3, 4],
        timezone="Europe/Amsterdam",
        urgent_override=True,
        enabled=True,
    )
    assert pol.quiet_start == "22:30"
    assert pol.urgent_override is True
    assert 5 not in pol.day_mask  # Saturday excluded


def test_send_request_and_preview_item():
    req = SendRequest(
        target_type="recipient",
        target_id="rec_1",
        priority=Priority.URGENT,
        title="Fire Alarm",
        message="Smoke detected in laundry room",
    )
    assert req.target_type == "recipient"
    assert req.priority == Priority.URGENT

    preview = PreviewItem(
        route_id="rt_1",
        route_name="Pixel",
        recipient_id="rec_1",
        recipient_name="Martijn",
        ha_service="notify.mobile_app_pixel",
        status=DeliveryStatus.SUBMITTED,
        reason="Dispatched",
    )
    assert preview.will_send is True
    assert preview.dedup_hit is False
    assert preview.service_target == "notify.mobile_app_pixel"


def test_delivery_record_model():
    record = DeliveryRecord(
        id="del_1",
        idempotency_key="req_123",
        created_utc=datetime.now(timezone.utc),
        priority=Priority.NORMAL,
        recipient_id="rec_1",
        recipient_name="Martijn",
        route_id="rt_1",
        ha_service="notify.mobile_app_pixel",
        status=DeliveryStatus.SUBMITTED,
    )
    assert record.status == DeliveryStatus.SUBMITTED
    assert record.priority == Priority.NORMAL
