"""Smart Break Window Optimizer and Time/Urgency Policy Engine."""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from app.models import (
    ActivityType,
    BreakAdviceStatus,
    BreakEvaluation,
    BreakWindow,
    LocationForecast,
    RainPoint,
    ScheduleUrgencyMode,
    SlotCandidate,
    UrgencyLevel,
    UserProfile,
)


def parse_hhmm(hhmm: str) -> int:
    """Convert 'HH:MM' into minutes since midnight (0..1439)."""
    try:
        parts = hhmm.strip().split(":", 1)
        h = max(0, min(23, int(parts[0])))
        m = max(0, min(59, int(parts[1])))
        return h * 60 + m
    except Exception:
        return 0


def format_hhmm(minutes_since_midnight: int) -> str:
    """Format minutes since midnight (mod 1440) as 'HH:MM'."""
    m_mod = minutes_since_midnight % 1440
    return f"{m_mod // 60:02d}:{m_mod % 60:02d}"


def is_time_in_window(current_min: int, start_min: int, end_min: int) -> bool:
    """Check if current_min falls within [start_min, end_min], supporting cross-midnight windows."""
    if start_min == end_min:
        return True
    if start_min < end_min:
        return start_min <= current_min <= end_min
    return current_min >= start_min or current_min <= end_min


def evaluate_user_schedule(
    user: UserProfile,
    now_local: Optional[datetime] = None,
    urgency_override: UrgencyLevel = UrgencyLevel.AUTO,
) -> Tuple[bool, str, str]:
    """
    Evaluate whether a notification is allowed right now for `user` and determine effective urgency ('urgent' | 'neutral').
    Returns: (allowed, effective_urgency, explanation)
    """
    try:
        tz = ZoneInfo(user.timezone or "Europe/Amsterdam")
    except Exception:
        tz = ZoneInfo("Europe/Amsterdam")

    dt = now_local.astimezone(tz) if now_local else datetime.now(tz)
    weekday = dt.weekday()
    cur_min = dt.hour * 60 + dt.minute
    start_min = parse_hhmm(user.window_start)
    end_min = parse_hhmm(user.window_end)

    in_day = weekday in (user.active_days or [])
    in_time = is_time_in_window(cur_min, start_min, end_min)
    in_window = in_day and in_time

    base_default = "urgent" if user.default_urgency == UrgencyLevel.URGENT else "neutral"

    if user.schedule_mode == ScheduleUrgencyMode.ALWAYS:
        eff = (
            urgency_override.value
            if urgency_override in (UrgencyLevel.URGENT, UrgencyLevel.NEUTRAL)
            else base_default
        )
        return True, eff, f"24/7 mode active ({eff})"

    if user.schedule_mode == ScheduleUrgencyMode.ACTIVE_WINDOW_ONLY:
        if not in_window:
            return (
                False,
                base_default,
                f"Suppressed: outside active hours ({user.window_start}–{user.window_end})",
            )
        eff = (
            urgency_override.value
            if urgency_override in (UrgencyLevel.URGENT, UrgencyLevel.NEUTRAL)
            else base_default
        )
        return True, eff, f"Within active hours ({user.window_start}–{user.window_end}) → {eff}"

    # ScheduleUrgencyMode.URGENT_WINDOW_ELSE_NEUTRAL
    if in_window:
        eff = (
            "neutral"
            if urgency_override == UrgencyLevel.NEUTRAL
            else "urgent"
        )
        return (
            True,
            eff,
            f"Within priority hours ({user.window_start}–{user.window_end}) → {eff.upper()}",
        )
    else:
        return (
            True,
            "neutral",
            f"Outside priority hours ({user.window_start}–{user.window_end}) → auto-downgraded to NEUTRAL",
        )


def _score_slot(
    slot_start_min: int,
    duration_minutes: int,
    planned_start_min: int,
    mm_by_minute: dict,
    rain_threshold_mm: float,
) -> SlotCandidate:
    samples: List[float] = []
    wet_mins = 0
    step = 5
    num_steps = max(1, duration_minutes // step)
    for i in range(num_steps):
        m = (slot_start_min + i * step) % 1440
        val = mm_by_minute.get(m, 0.0)
        samples.append(val)
        if val >= rain_threshold_mm:
            wet_mins += step

    max_mm = round(max(samples) if samples else 0.0, 2)
    avg_mm = round(sum(samples) / len(samples) if samples else 0.0, 2)
    is_dry = max_mm < rain_threshold_mm
    shift = slot_start_min - planned_start_min

    return SlotCandidate(
        start_time=format_hhmm(slot_start_min),
        end_time=format_hhmm(slot_start_min + duration_minutes),
        shift_minutes=shift,
        max_mm_h=max_mm,
        avg_mm_h=avg_mm,
        wet_minutes=wet_mins,
        is_dry=is_dry,
    )


def evaluate_break_window(
    brk: BreakWindow,
    user: UserProfile,
    forecast: LocationForecast,
    rain_threshold_mm: float = 0.15,
    location_source: str = "fixed",
    now_local: Optional[datetime] = None,
) -> BreakEvaluation:
    """
    Evaluate a BreakWindow against a LocationForecast and compute the optimal dry/cleanest slot
    before, during, or after the scheduled break.
    """
    try:
        tz = ZoneInfo(user.timezone or "Europe/Amsterdam")
    except Exception:
        tz = ZoneInfo("Europe/Amsterdam")

    dt_now = now_local.astimezone(tz) if now_local else datetime.now(tz)

    # Build lookup map from minute-of-day -> mm/h
    mm_by_min: dict = {}
    for pt in forecast.points:
        m = parse_hhmm(pt.time_label)
        # Keep the nearest/today point for that HH:MM
        if m not in mm_by_min or abs(pt.minutes_from_now) < 360:
            mm_by_min[m] = pt.mm_per_hour

    planned_start_min = parse_hhmm(brk.start_time)
    duration = max(5, brk.duration_minutes)
    planned_end_min = planned_start_min + duration

    earliest_start = planned_start_min - brk.flex_before_minutes
    latest_start = planned_start_min + brk.flex_after_minutes

    candidates: List[SlotCandidate] = []
    cur_start = earliest_start
    while cur_start <= latest_start:
        cand = _score_slot(
            slot_start_min=cur_start,
            duration_minutes=duration,
            planned_start_min=planned_start_min,
            mm_by_minute=mm_by_min,
            rain_threshold_mm=rain_threshold_mm,
        )
        candidates.append(cand)
        cur_start += 5

    planned_slot = next(
        (c for c in candidates if c.shift_minutes == 0),
        _score_slot(planned_start_min, duration, planned_start_min, mm_by_min, rain_threshold_mm),
    )

    schedule_allowed, eff_urgency, schedule_reason = evaluate_user_schedule(
        user=user,
        now_local=dt_now,
        urgency_override=brk.urgency_override,
    )

    activity_label = {
        ActivityType.WALK: "walk",
        ActivityType.BIKE: "bike ride",
        ActivityType.RUN: "run",
        ActivityType.BREAK: "break",
    }.get(brk.activity_type, "break")

    if planned_slot.is_dry:
        # Check if rain starts within 15 minutes right after planned_end
        after_slot = _score_slot(planned_end_min, 15, planned_start_min, mm_by_min, rain_threshold_mm)
        if not after_slot.is_dry:
            status = BreakAdviceStatus.DRY_BUT_RAIN_SOON_AFTER
            recommended = planned_slot
            headline = f"Leave on time at {planned_slot.start_time} — rain starts right after {planned_slot.end_time}!"
            advice = (
                f"Your planned {planned_slot.start_time}–{planned_slot.end_time} {activity_label} at {forecast.location_name} "
                f"is dry (0.0 mm/h), but rain ({after_slot.max_mm_h:.1f} mm/h) arrives between "
                f"{after_slot.start_time}–{after_slot.end_time}. Go on time or slightly earlier!"
            )
            should_notify = schedule_allowed
        else:
            status = BreakAdviceStatus.DRY_ON_SCHEDULE
            recommended = planned_slot
            headline = f"All clear for {planned_slot.start_time}–{planned_slot.end_time} (Dry)"
            advice = (
                f"Dry weather expected during your {planned_slot.start_time}–{planned_slot.end_time} "
                f"{activity_label} at {forecast.location_name} (max {planned_slot.max_mm_h:.2f} mm/h)."
            )
            should_notify = bool(brk.notify_when_dry and schedule_allowed)
    else:
        # Planned slot has rain! Search for dry alternatives first
        dry_candidates = [c for c in candidates if c.is_dry]
        if dry_candidates:
            # Prefer smallest absolute shift; if tied, prefer earlier (negative shift)
            dry_candidates.sort(key=lambda c: (abs(c.shift_minutes), 0 if c.shift_minutes < 0 else 1, c.avg_mm_h))
            recommended = dry_candidates[0]
            shift_abs = abs(recommended.shift_minutes)
            if recommended.shift_minutes < 0:
                status = BreakAdviceStatus.SHIFT_EARLIER_DRY
                headline = f"Go {shift_abs} min earlier! {recommended.start_time}–{recommended.end_time} is dry"
                advice = (
                    f"Rain expected during your {planned_slot.start_time}–{planned_slot.end_time} {activity_label} "
                    f"at {forecast.location_name} (peak {planned_slot.max_mm_h:.1f} mm/h). "
                    f"Leave {shift_abs} min earlier ({recommended.start_time}–{recommended.end_time}) for a completely dry window!"
                )
            else:
                status = BreakAdviceStatus.SHIFT_LATER_DRY
                headline = f"Wait {shift_abs} min! {recommended.start_time}–{recommended.end_time} is dry"
                advice = (
                    f"Rain expected during your {planned_slot.start_time}–{planned_slot.end_time} {activity_label} "
                    f"at {forecast.location_name} (peak {planned_slot.max_mm_h:.1f} mm/h). "
                    f"Shift {shift_abs} min later ({recommended.start_time}–{recommended.end_time}) for a dry window!"
                )
            should_notify = schedule_allowed
        else:
            # No completely dry slot; look for the cleanest slot
            cleaner = sorted(candidates, key=lambda c: (c.avg_mm_h, c.max_mm_h, abs(c.shift_minutes)))
            best = cleaner[0] if cleaner else planned_slot
            if best.shift_minutes != 0 and best.avg_mm_h <= planned_slot.avg_mm_h * 0.65:
                status = BreakAdviceStatus.SHIFT_CLEANER_SLOT
                recommended = best
                direction = "earlier" if best.shift_minutes < 0 else "later"
                shift_abs = abs(best.shift_minutes)
                headline = (
                    f"Lighter rain {shift_abs} min {direction} ({best.start_time}–{best.end_time}: {best.max_mm_h:.1f} mm/h)"
                )
                advice = (
                    f"No completely dry {duration}-min window near {planned_slot.start_time} at {forecast.location_name} "
                    f"(planned peak {planned_slot.max_mm_h:.1f} mm/h). Best available slot is {shift_abs} min {direction} "
                    f"at {best.start_time}–{best.end_time} (max {best.max_mm_h:.1f} mm/h)."
                )
            else:
                status = BreakAdviceStatus.HEAVY_RAIN_NO_WINDOW
                recommended = planned_slot
                headline = f"Continuous rain across { format_hhmm(earliest_start) }–{ format_hhmm(latest_start + duration) }"
                advice = (
                    f"Persistent rain expected at {forecast.location_name} before, during, and after your "
                    f"{planned_slot.start_time}–{planned_slot.end_time} {activity_label} (peak {planned_slot.max_mm_h:.1f} mm/h). "
                    f"Bring rain gear or reschedule outside this window."
                )
            should_notify = schedule_allowed

    return BreakEvaluation(
        break_id=brk.id,
        break_name=brk.name,
        user_id=user.id,
        user_name=user.name,
        activity_type=brk.activity_type,
        location_id=forecast.location_id,
        location_name=forecast.location_name,
        location_source=location_source,
        latitude=forecast.latitude,
        longitude=forecast.longitude,
        planned_start=planned_slot.start_time,
        planned_end=planned_slot.end_time,
        duration_minutes=duration,
        flex_before_minutes=brk.flex_before_minutes,
        flex_after_minutes=brk.flex_after_minutes,
        status=status,
        effective_urgency=eff_urgency,
        schedule_allowed=schedule_allowed,
        schedule_reason=schedule_reason,
        should_notify=should_notify,
        headline=headline,
        advice_text=advice,
        planned_slot=planned_slot,
        recommended_slot=recommended,
        all_candidates=candidates,
    )
