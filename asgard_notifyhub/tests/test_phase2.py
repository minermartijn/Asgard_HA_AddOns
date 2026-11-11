"""v0.1.5 regression tests: dispatch outcome aggregation, route/policy validation, timezones."""

import asyncio
from datetime import datetime, timezone

import pytest

from app.client import DemoHomeAssistantClient
from app.engine import RoutingEngine, evaluate_quiet_hours
from app.models import (
    DeliveryRecord,
    DeliveryStatus,
    Priority,
    QuietPolicy,
    Recipient,
    RecipientGroup,
    Route,
    SendRequest,
    TargetType,
    summarize_records,
)
from app.storage import Storage
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Outcome aggregation
# ---------------------------------------------------------------------------

def _rec(status):
    return DeliveryRecord(id="x", priority=Priority.NORMAL, status=status)


@pytest.mark.parametrize(
    "statuses,outcome",
    [
        ([], "no_routes"),
        ([DeliveryStatus.SUBMITTED, DeliveryStatus.SUBMITTED], "submitted"),
        ([DeliveryStatus.SUBMITTED, DeliveryStatus.FAILED], "partial"),
        ([DeliveryStatus.SUBMITTED, DeliveryStatus.BLOCKED_QUIET_HOURS], "partial"),
        ([DeliveryStatus.BLOCKED_QUIET_HOURS], "suppressed"),
        ([DeliveryStatus.SUPPRESSED_DUPLICATE, DeliveryStatus.BLOCKED_PRIORITY], "suppressed"),
        ([DeliveryStatus.ROUTE_DISABLED, DeliveryStatus.RECIPIENT_DISABLED], "suppressed"),
        ([DeliveryStatus.FAILED], "failed"),
        ([DeliveryStatus.INVALID_ROUTE, DeliveryStatus.BLOCKED_QUIET_HOURS], "failed"),
    ],
)
def test_summarize_records(statuses, outcome):
    summary = summarize_records([_rec(s) for s in statuses])
    assert summary.outcome == outcome
    assert summary.total == len(statuses)


def _engine(tmp_path, client=None):
    storage = Storage(tmp_path / "t.db")
    return storage, RoutingEngine(storage=storage, ha_client=client or DemoHomeAssistantClient())


def test_priority_block_is_distinct_from_disabled_route(tmp_path):
    storage, engine = _engine(tmp_path)
    storage.save_recipient(Recipient(id="r1", name="Martijn", timezone="Europe/Amsterdam"))
    storage.save_route(Route(id="a", recipient_id="r1", name="Phone", ha_service="mobile_app_pixel",
                             priority_min=Priority.URGENT))
    storage.save_route(Route(id="b", recipient_id="r1", name="Old", ha_service="mobile_app_old", enabled=False))
    preview = engine.preview(SendRequest(recipient_id="r1", message="m", priority=Priority.NORMAL))
    by_route = {i.route_id: i for i in preview.items}
    assert by_route["a"].status == DeliveryStatus.BLOCKED_PRIORITY
    assert "below route minimum" in by_route["a"].reason
    assert by_route["b"].status == DeliveryStatus.ROUTE_DISABLED


def test_stored_dismiss_route_is_never_dispatched(tmp_path):
    client = DemoHomeAssistantClient()
    storage, engine = _engine(tmp_path, client)
    storage.save_recipient(Recipient(id="r1", name="Admin"))
    # Simulates a route created by an older version before the action-level allowlist.
    storage.save_route(Route(id="bad", recipient_id="r1", name="Dismiss",
                             ha_domain="persistent_notification", ha_service="dismiss_all"))
    storage.save_route(Route(id="good", recipient_id="r1", name="Panel",
                             ha_domain="persistent_notification", ha_service="create"))
    records = asyncio.run(engine.execute(SendRequest(recipient_id="r1", message="hello")))
    statuses = {r.route_id: r.status for r in records}
    assert statuses["bad"] == DeliveryStatus.INVALID_ROUTE
    assert statuses["good"] == DeliveryStatus.SUBMITTED
    assert [c["service"] for c in client.dispatched_calls] == ["create"]
    assert summarize_records(records).outcome == "partial"


def test_global_policy_applies_to_every_recipient(tmp_path):
    storage, engine = _engine(tmp_path)
    storage.save_recipient(Recipient(id="r1", name="A"))
    storage.save_route(Route(id="a", recipient_id="r1", name="P", ha_service="mobile_app_pixel"))
    storage.save_policy(QuietPolicy(id="g", target_id="household_global", target_type=TargetType.GLOBAL,
                                    quiet_start="00:00", quiet_end="23:59", timezone="UTC"))
    preview = engine.preview(SendRequest(recipient_id="r1", message="m"),
                             now_utc=datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc))
    assert preview.items[0].status == DeliveryStatus.BLOCKED_QUIET_HOURS


def test_group_policy_applies_to_members_when_sending_to_everyone(tmp_path):
    storage, engine = _engine(tmp_path)
    storage.save_recipient(Recipient(id="r1", name="A"))
    storage.save_recipient(Recipient(id="r2", name="B"))
    for rid in ("r1", "r2"):
        storage.save_route(Route(id=f"rt_{rid}", recipient_id=rid, name="P", ha_service="mobile_app_pixel"))
    storage.save_group(RecipientGroup(id="kids", name="Kids", recipient_ids=["r2"]))
    storage.save_policy(QuietPolicy(id="p", target_id="kids", target_type=TargetType.GROUP,
                                    quiet_start="20:00", quiet_end="07:00", timezone="Europe/Amsterdam"))
    # 21:30 Amsterdam (winter, UTC+1) == 20:30 UTC
    preview = engine.preview(SendRequest(target_type="all", message="m"),
                             now_utc=datetime(2026, 1, 14, 20, 30, tzinfo=timezone.utc))
    st = {i.recipient_id: i.status for i in preview.items}
    assert st == {"r1": DeliveryStatus.SUBMITTED, "r2": DeliveryStatus.BLOCKED_QUIET_HOURS}


# ---------------------------------------------------------------------------
# Europe/Amsterdam quiet hours (CET/CEST, DST transitions)
# ---------------------------------------------------------------------------

AMS = "Europe/Amsterdam"


def _pol(**kw):
    base = dict(id="p", target_id="r", quiet_start="22:00", quiet_end="07:00", timezone=AMS)
    base.update(kw)
    return QuietPolicy(**base)


@pytest.mark.parametrize(
    "utc_dt,expected",
    [
        # Winter (CET, UTC+1): 21:30 UTC = 22:30 local -> quiet
        (datetime(2026, 1, 14, 21, 30, tzinfo=timezone.utc), True),
        # Winter: 20:30 UTC = 21:30 local -> not quiet
        (datetime(2026, 1, 14, 20, 30, tzinfo=timezone.utc), False),
        # Summer (CEST, UTC+2): 20:30 UTC = 22:30 local -> quiet
        (datetime(2026, 7, 15, 20, 30, tzinfo=timezone.utc), True),
        # Summer: 05:30 UTC = 07:30 local -> not quiet
        (datetime(2026, 7, 15, 5, 30, tzinfo=timezone.utc), False),
        # Summer: 04:30 UTC = 06:30 local -> quiet (morning part)
        (datetime(2026, 7, 15, 4, 30, tzinfo=timezone.utc), True),
    ],
)
def test_amsterdam_winter_and_summer(utc_dt, expected):
    quiet, _ = evaluate_quiet_hours(_pol(), Priority.NORMAL, now_utc=utc_dt)
    assert quiet is expected


def test_amsterdam_spring_forward_transition():
    # 2026-03-29: clocks jump 02:00 -> 03:00 local (01:00 UTC).
    pol = _pol(quiet_start="01:00", quiet_end="03:30")
    # 00:30 UTC = 01:30 CET -> quiet
    assert evaluate_quiet_hours(pol, Priority.NORMAL, now_utc=datetime(2026, 3, 29, 0, 30, tzinfo=timezone.utc))[0]
    # 01:15 UTC = 03:15 CEST -> still quiet
    assert evaluate_quiet_hours(pol, Priority.NORMAL, now_utc=datetime(2026, 3, 29, 1, 15, tzinfo=timezone.utc))[0]
    # 01:45 UTC = 03:45 CEST -> over
    assert not evaluate_quiet_hours(pol, Priority.NORMAL, now_utc=datetime(2026, 3, 29, 1, 45, tzinfo=timezone.utc))[0]


def test_amsterdam_fall_back_transition():
    # 2026-10-25: clocks fall back 03:00 -> 02:00 local (01:00 UTC).
    pol = _pol(quiet_start="22:00", quiet_end="07:00")
    # 05:30 UTC = 06:30 CET -> quiet
    assert evaluate_quiet_hours(pol, Priority.NORMAL, now_utc=datetime(2026, 10, 25, 5, 30, tzinfo=timezone.utc))[0]
    # 06:30 UTC = 07:30 CET -> not quiet (would be wrong if CEST offset were still used)
    assert not evaluate_quiet_hours(pol, Priority.NORMAL, now_utc=datetime(2026, 10, 25, 6, 30, tzinfo=timezone.utc))[0]


def test_amsterdam_weekday_mask_cross_midnight():
    # Policy active only on Friday (4) nights: Fri 22:00 -> Sat 07:00 local.
    pol = _pol(day_mask=[4])
    # Sat 2026-07-18 06:00 local (04:00 UTC) belongs to Friday night -> quiet
    assert evaluate_quiet_hours(pol, Priority.NORMAL, now_utc=datetime(2026, 7, 18, 4, 0, tzinfo=timezone.utc))[0]
    # Sat 2026-07-18 23:00 local (21:00 UTC) -> Saturday night not in mask
    assert not evaluate_quiet_hours(pol, Priority.NORMAL, now_utc=datetime(2026, 7, 18, 21, 0, tzinfo=timezone.utc))[0]
    # Thu 2026-07-16 23:00 local -> not in mask
    assert not evaluate_quiet_hours(pol, Priority.NORMAL, now_utc=datetime(2026, 7, 16, 21, 0, tzinfo=timezone.utc))[0]


def test_per_recipient_timezones_differ():
    utc_now = datetime(2026, 7, 15, 21, 30, tzinfo=timezone.utc)  # 23:30 Amsterdam, 17:30 New York
    assert evaluate_quiet_hours(_pol(timezone=AMS), Priority.NORMAL, now_utc=utc_now)[0]
    assert not evaluate_quiet_hours(_pol(timezone="America/New_York"), Priority.NORMAL, now_utc=utc_now)[0]


def test_explicit_utc_policy_is_not_reinterpreted():
    # 22:30 UTC in summer is 00:30 in Amsterdam; a UTC policy 22:00-23:00 must still be quiet.
    pol = _pol(quiet_start="22:00", quiet_end="23:00", timezone="UTC")
    assert evaluate_quiet_hours(pol, Priority.NORMAL, now_utc=datetime(2026, 7, 15, 22, 30, tzinfo=timezone.utc))[0]


# ---------------------------------------------------------------------------
# HTTP API validation
# ---------------------------------------------------------------------------

def test_route_api_rejects_dismiss_actions(client):
    for svc in ("dismiss", "dismiss_all"):
        res = client.post("/api/routes", json={
            "recipient_id": "rec_admin", "name": "x",
            "ha_domain": "persistent_notification", "ha_service": svc,
        })
        assert res.status_code == 400
        assert "not a delivery action" in res.json()["detail"]
    res = client.post("/api/routes", json={
        "recipient_id": "rec_admin", "name": "x", "ha_domain": "light", "ha_service": "turn_on",
    })
    assert res.status_code == 400
    ok = client.post("/api/routes", json={
        "recipient_id": "rec_admin", "name": "Panel", "ha_domain": "persistent_notification", "ha_service": "create",
    })
    assert ok.status_code == 200


def test_route_api_supports_edit(client):
    res = client.post("/api/routes", json={
        "recipient_id": "rec_admin", "name": "Phone", "ha_domain": "notify", "ha_service": "mobile_app_pixel",
    })
    rid = res.json()["route"]["id"]
    upd = client.post("/api/routes", json={
        "id": rid, "recipient_id": "rec_admin", "name": "Phone", "ha_domain": "notify",
        "ha_service": "mobile_app_pixel", "priority_min": "urgent", "enabled": False,
    })
    assert upd.status_code == 200
    rec = next(r for r in client.get("/api/recipients").json()["recipients"] if r["id"] == "rec_admin")
    rt = next(r for r in rec["routes"] if r["id"] == rid)
    assert rt["priority_min"] == "urgent" and rt["enabled"] is False


def test_policy_api_validates_target_and_timezone(client):
    bad_target = client.post("/api/policies", json={"target_id": "rec_missing", "target_type": "recipient"})
    assert bad_target.status_code == 400
    assert "does not exist" in bad_target.json()["detail"]
    bad_tz = client.post("/api/policies", json={
        "target_id": "rec_admin", "target_type": "recipient", "timezone": "Mars/Olympus",
    })
    assert bad_tz.status_code == 400
    bad_time = client.post("/api/policies", json={
        "target_id": "rec_admin", "target_type": "recipient", "quiet_start": "25:00",
    })
    assert bad_time.status_code == 400
    ok = client.post("/api/policies", json={
        "target_id": "rec_admin", "target_type": "recipient", "timezone": "Europe/Amsterdam",
        "quiet_start": "23:00", "quiet_end": "06:30", "day_mask": [0, 1, 2, 3, 4],
    })
    assert ok.status_code == 200
    pid = ok.json()["policy"]["id"]
    # Edit existing policy keeps id
    edit = client.post("/api/policies", json={
        "id": pid, "target_id": "rec_admin", "target_type": "recipient", "timezone": "Europe/Amsterdam",
        "quiet_start": "22:30", "quiet_end": "06:30", "day_mask": [5, 6],
    })
    assert edit.status_code == 200
    pols = {p["id"]: p for p in client.get("/api/policies").json()["policies"]}
    assert pols[pid]["quiet_start"] == "22:30" and pols[pid]["day_mask"] == [5, 6]


def test_orphaned_policy_is_flagged_and_preserved(app, client):
    storage = app.state.service.storage
    storage.save_policy(QuietPolicy(id="pol_orphan", target_id="rec_deleted", target_type=TargetType.RECIPIENT,
                                    timezone="UTC"))
    pols = {p["id"]: p for p in client.get("/api/policies").json()["policies"]}
    assert pols["pol_orphan"]["orphaned"] is True
    assert pols["pol_orphan"]["timezone"] == "UTC"  # explicit UTC preserved
    assert pols["pol_admin_night"]["orphaned"] is False


def test_recipient_api_validates_timezone(client):
    assert client.post("/api/recipients", json={"name": "X", "timezone": "Nowhere/City"}).status_code == 400
    ok = client.post("/api/recipients", json={"name": "Martijn", "timezone": "Europe/Amsterdam"})
    assert ok.status_code == 200 and ok.json()["recipient"]["timezone"] == "Europe/Amsterdam"


def test_send_api_returns_accurate_summary(app, client):
    svc = app.state.service
    svc.storage.save_recipient(Recipient(id="r_mix", name="Mixed"))
    svc.storage.save_route(Route(id="ok", recipient_id="r_mix", name="Phone", ha_service="mobile_app_pixel"))
    svc.storage.save_route(Route(id="watch", recipient_id="r_mix", name="Watch", ha_service="galaxy_watch5_fhyw"))
    svc.ha_client.fail_actions["notify.galaxy_watch5_fhyw"] = "integration error (HTTP 500)"
    res = client.post("/api/send", json={"recipient_id": "r_mix", "message": "mixed", "priority": "urgent"})
    data = res.json()
    assert data["summary"]["outcome"] == "partial"
    assert data["summary"]["counts"] == {"submitted": 1, "failed": 1}

    # Same message again -> duplicate for the phone, failure for the watch? No: dedup is checked
    # against submitted messages for the recipient, so both routes are suppressed now.
    again = client.post("/api/send", json={"recipient_id": "r_mix", "message": "mixed", "priority": "urgent"}).json()
    assert again["summary"]["outcome"] == "suppressed"
    assert again["summary"]["submitted"] == 0


def test_send_api_quiet_hours_only_is_suppressed(app, client):
    svc = app.state.service
    svc.storage.save_recipient(Recipient(id="r_q", name="Quiet"))
    svc.storage.save_route(Route(id="rq", recipient_id="r_q", name="Phone", ha_service="mobile_app_pixel"))
    svc.storage.save_policy(QuietPolicy(id="pq", target_id="r_q", quiet_start="00:00", quiet_end="23:59",
                                        timezone="UTC", urgent_override=False))
    data = client.post("/api/send", json={"recipient_id": "r_q", "message": "night"}).json()
    assert data["summary"]["outcome"] == "suppressed"
    assert data["records"][0]["status"] == "blocked_quiet_hours"


def test_restart_persistence(tmp_path):
    """Configuration survives a simulated App restart (new Storage on the same DB file)."""
    from app.main import create_app
    from app.service import NotifyHubService
    from app.settings import Settings

    db = tmp_path / "persist.db"

    def boot():
        storage = Storage(db)
        svc = NotifyHubService(storage=storage, ha_client=DemoHomeAssistantClient(), demo_mode=True)
        cfg = Settings(data_dir=tmp_path, allowed_source_ips="*", demo_mode=True)
        return TestClient(create_app(settings=cfg, service=svc))

    c1 = boot()
    rid = c1.post("/api/recipients", json={"name": "Persisted", "timezone": "Europe/Amsterdam"}).json()["recipient"]["id"]
    c1.post("/api/policies", json={"target_id": rid, "target_type": "recipient", "timezone": "Europe/Amsterdam"})
    c2 = boot()
    names = [r["name"] for r in c2.get("/api/recipients").json()["recipients"]]
    assert "Persisted" in names
    assert any(p["target_id"] == rid for p in c2.get("/api/policies").json()["policies"])
