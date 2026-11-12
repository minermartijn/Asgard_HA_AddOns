"""Unit tests for the ASGARD RainBreak weather parser, schedule/urgency engine, and break optimizer."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.ha_client import is_allowed_notify_action, resolve_user_target_locations
from app.models import (
    ActivityType,
    BreakAdviceStatus,
    BreakWindow,
    DiscoveredPerson,
    LocationForecast,
    LocationMode,
    RainPoint,
    SavedLocation,
    ScheduleUrgencyMode,
    UrgencyLevel,
    UserProfile,
)
from app.optimizer import evaluate_break_window, evaluate_user_schedule
from app.weather import buienradar_raw_to_mm_h, parse_buienradar_text


def test_buienradar_formula_and_parser():
    assert buienradar_raw_to_mm_h(0) == 0.0
    # 109 corresponds to 10^0 = 1.0 mm/h
    assert buienradar_raw_to_mm_h(109) == 1.0
    assert buienradar_raw_to_mm_h(141) == 10.0

    tz = ZoneInfo("Europe/Amsterdam")
    now_dt = datetime(2026, 11, 12, 9, 40, tzinfo=tz)
    raw = "000|09:40\n000|09:45\n000|09:50\n000|09:55\n120|10:00\n125|10:05\n115|10:10\n000|10:15\n"
    pts = parse_buienradar_text(raw, now_dt)
    assert len(pts) == 8
    assert pts[0].mm_per_hour == 0.0
    assert pts[4].time_label == "10:00"
    assert pts[4].mm_per_hour > 2.0


def test_schedule_urgency_modes():
    tz = ZoneInfo("Europe/Amsterdam")
    user = UserProfile(
        id="usr_test",
        name="Martijn",
        schedule_mode=ScheduleUrgencyMode.URGENT_WINDOW_ELSE_NEUTRAL,
        window_start="08:00",
        window_end="17:30",
        active_days=[0, 1, 2, 3, 4],  # Mon-Fri
        default_urgency=UrgencyLevel.URGENT,
        timezone="Europe/Amsterdam",
    )

    # Thursday 10:00 -> inside window -> Urgent
    dt_inside = datetime(2026, 11, 12, 10, 0, tzinfo=tz)
    allowed, urg, reason = evaluate_user_schedule(user, now_local=dt_inside)
    assert allowed is True
    assert urg == "urgent"

    # Thursday 20:30 -> outside window -> still allowed, downgraded to Neutral!
    dt_outside = datetime(2026, 11, 12, 20, 30, tzinfo=tz)
    allowed2, urg2, reason2 = evaluate_user_schedule(user, now_local=dt_outside)
    assert allowed2 is True
    assert urg2 == "neutral"

    # Active window only mode -> outside window is suppressed (allowed=False)
    user.schedule_mode = ScheduleUrgencyMode.ACTIVE_WINDOW_ONLY
    allowed3, _, _ = evaluate_user_schedule(user, now_local=dt_outside)
    assert allowed3 is False
    allowed4, urg4, _ = evaluate_user_schedule(user, now_local=dt_inside)
    assert allowed4 is True
    assert urg4 == "urgent"


def test_break_optimizer_recommends_15_min_earlier_when_1000_break_has_rain():
    """Exact user story: 10:00 (15m break) has rain, 09:45-10:00 is dry -> recommends going 15 min earlier."""
    tz = ZoneInfo("Europe/Amsterdam")
    now_dt = datetime(2026, 11, 12, 9, 30, tzinfo=tz)

    pts = []
    # 09:30 to 09:55 is completely dry (0.0 mm/h)
    for m in (30, 35, 40, 45, 50, 55):
        pts.append(
            RainPoint(
                timestamp_iso=f"2026-11-12T09:{m:02d}:00+01:00",
                time_label=f"09:{m:02d}",
                minutes_from_now=m - 30,
                mm_per_hour=0.0,
                probability_pct=0,
            )
        )
    # 10:00 to 10:25 has heavy rain (2.5 mm/h)
    for m in (0, 5, 10, 15, 20, 25, 30, 35, 40, 45):
        pts.append(
            RainPoint(
                timestamp_iso=f"2026-11-12T10:{m:02d}:00+01:00",
                time_label=f"10:{m:02d}",
                minutes_from_now=30 + m,
                mm_per_hour=2.5,
                probability_pct=90,
            )
        )

    fc = LocationForecast(
        location_id="loc_work",
        location_name="Work / Office",
        latitude=52.0907,
        longitude=5.1214,
        source_used="Buienradar 5m",
        fetched_at=now_dt.isoformat(),
        is_currently_raining=False,
        current_mm_h=0.0,
        points=pts,
    )

    user = UserProfile(id="usr_1", name="Martijn")
    brk = BreakWindow(
        id="brk_1000",
        user_id="usr_1",
        name="Morning Walk (10:00)",
        activity_type=ActivityType.WALK,
        start_time="10:00",
        duration_minutes=15,
        flex_before_minutes=30,
        flex_after_minutes=30,
    )

    ev = evaluate_break_window(brk, user, fc, rain_threshold_mm=0.15, now_local=now_dt)
    assert ev.status == BreakAdviceStatus.SHIFT_EARLIER_DRY
    assert ev.recommended_slot.start_time == "09:45"
    assert ev.recommended_slot.end_time == "10:00"
    assert ev.recommended_slot.shift_minutes == -15
    assert ev.recommended_slot.is_dry is True
    assert "15 min earlier" in ev.headline


def test_break_optimizer_recommends_later_slot_when_morning_wet_and_after_dry():
    tz = ZoneInfo("Europe/Amsterdam")
    now_dt = datetime(2026, 11, 12, 12, 0, tzinfo=tz)

    pts = []
    # 12:00 to 12:40 is raining (2.0 mm/h)
    for m in range(0, 45, 5):
        pts.append(
            RainPoint(
                timestamp_iso=f"2026-11-12T12:{m:02d}:00+01:00",
                time_label=f"12:{m:02d}",
                minutes_from_now=m,
                mm_per_hour=2.0,
                probability_pct=85,
            )
        )
    # 12:45 to 13:30 is dry (0.0 mm/h)
    for m in (45, 50, 55):
        pts.append(
            RainPoint(
                timestamp_iso=f"2026-11-12T12:{m:02d}:00+01:00",
                time_label=f"12:{m:02d}",
                minutes_from_now=m,
                mm_per_hour=0.0,
                probability_pct=0,
            )
        )
    for m in range(0, 35, 5):
        pts.append(
            RainPoint(
                timestamp_iso=f"2026-11-12T13:{m:02d}:00+01:00",
                time_label=f"13:{m:02d}",
                minutes_from_now=60 + m,
                mm_per_hour=0.0,
                probability_pct=0,
            )
        )

    fc = LocationForecast(
        location_id="loc_work",
        location_name="Work / Office",
        latitude=52.0907,
        longitude=5.1214,
        source_used="Buienradar 5m",
        fetched_at=now_dt.isoformat(),
        is_currently_raining=True,
        current_mm_h=2.0,
        points=pts,
    )

    user = UserProfile(id="usr_1", name="Martijn")
    brk = BreakWindow(
        id="brk_1230",
        user_id="usr_1",
        name="Lunch Walk (12:30)",
        activity_type=ActivityType.WALK,
        start_time="12:30",
        duration_minutes=30,
        flex_before_minutes=30,
        flex_after_minutes=30,
    )

    ev = evaluate_break_window(brk, user, fc, rain_threshold_mm=0.15, now_local=now_dt)
    assert ev.status == BreakAdviceStatus.SHIFT_LATER_DRY
    assert ev.recommended_slot.start_time == "12:45"
    assert ev.recommended_slot.end_time == "13:15"
    assert ev.recommended_slot.shift_minutes == 15


def test_user_location_resolution_modes():
    locs = [
        SavedLocation(id="loc_home", name="Home", latitude=52.3676, longitude=4.9041),
        SavedLocation(id="loc_work", name="Work", latitude=52.0907, longitude=5.1214),
    ]
    persons = [
        DiscoveredPerson(
            entity_id="person.martijn",
            name="Martijn",
            state="work",
            latitude=52.1111,
            longitude=5.2222,
        )
    ]

    user = UserProfile(
        id="usr_1",
        name="Martijn",
        ha_person_entity="person.martijn",
        location_mode=LocationMode.LIVE_PERSON,
        fixed_location_id="loc_work",
        fallback_location_id="loc_home",
        watched_location_ids=["loc_home", "loc_work"],
    )

    # 1. Live person mode uses person.martijn GPS coordinates
    res_live = resolve_user_target_locations(user, locs, persons)
    assert len(res_live) == 1
    assert res_live[0][2] == 52.1111
    assert res_live[0][3] == 5.2222
    assert "Live Location" in res_live[0][1]

    # 2. Fixed location mode uses loc_work
    user.location_mode = LocationMode.FIXED_LOCATION
    res_fixed = resolve_user_target_locations(user, locs, persons)
    assert len(res_fixed) == 1
    assert res_fixed[0][0] == "loc_work"

    # 3. Multi-location mode returns both loc_home and loc_work
    user.location_mode = LocationMode.MULTI_LOCATION
    res_multi = resolve_user_target_locations(user, locs, persons)
    assert len(res_multi) == 2


def test_notify_action_allowlist():
    assert is_allowed_notify_action("notify.mobile_app_mart_s25") is True
    assert is_allowed_notify_action("persistent_notification.create") is True
    assert is_allowed_notify_action("notify.send_message") is False
    assert is_allowed_notify_action("persistent_notification.dismiss") is False
    assert is_allowed_notify_action("persistent_notification.dismiss_all") is False
