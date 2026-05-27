"""
Feeding amount calculator and smart schedule generator.
"""
from typing import List, Optional, Dict, Tuple
import math


# ──────────────── Amount Calculator ────────────────

def calculate_feeding_amount(weight_g: float, num_feedings: int) -> dict:
    """
    Calculate recommended feeding amount per bottle.

    Formula: weight_g * 155 / num_feedings = ml per feeding
    (WHO-based guideline: ~150-155 ml per kg body weight per day)

    Returns dict with raw, rounded to 5ml, and rounded to 10ml values.
    """
    daily_total = weight_g * 155 / 1000  # total ml/day
    per_feeding_raw = daily_total / num_feedings
    per_feeding_5 = round_to_nearest(per_feeding_raw, 5)
    per_feeding_10 = math.floor(per_feeding_raw / 10) * 10

    return {
        "weight_g": weight_g,
        "num_feedings": num_feedings,
        "daily_total_ml": round(daily_total, 1),
        "per_feeding_ml": round(per_feeding_raw, 1),
        "per_feeding_rounded": per_feeding_5,
        "per_feeding_floor10": per_feeding_10,
        "formula": f"{weight_g}g × 155 ÷ 1000 ÷ {num_feedings} = {per_feeding_raw:.1f}ml",
    }


def round_to_nearest(value: float, nearest: int) -> float:
    """Round value to nearest multiple."""
    return round(round(value / nearest) * nearest, 1)


# ──────────────── Time Utilities ────────────────

def parse_hhmm(time_str: str) -> int:
    """Parse HH:MM string to minutes since midnight."""
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {time_str}")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Invalid time values: {time_str}")
    return h * 60 + m


def minutes_to_hhmm(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM string."""
    minutes = int(minutes) % (24 * 60)
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def is_in_window(minutes: int, start: int, end: int) -> bool:
    """Check if a time (in minutes) falls within a window [start, end]."""
    minutes = minutes % (24 * 60)
    if start <= end:
        return start <= minutes <= end
    else:
        # Window wraps midnight
        return minutes >= start or minutes <= end


def window_conflicts(feeding_min: int, window_end_min: int, feeding_start: int,
                     window_start: int, window_end: int, burp_buffer: int) -> bool:
    """
    Check if a feeding + its burp time conflicts with a blocked window.
    Feeding occupies [feeding_start, feeding_start + burp_buffer].
    """
    feed_end = feeding_start + burp_buffer
    # Simple non-wrapping check
    if window_start <= window_end:
        # Does [feeding_start, feed_end] overlap with [window_start, window_end]?
        return feeding_start < window_end and feed_end > window_start
    else:
        # Window wraps midnight - split into two checks
        return (feeding_start < (24 * 60) and feed_end > window_start) or \
               (feeding_start < window_end)


# ──────────────── Schedule Generator ────────────────

def calculate_schedule(
    num_feedings: int,
    first_feeding_time: str,
    last_feeding_time: Optional[str] = None,
    blocked_windows: Optional[List[Dict]] = None,
    burp_buffer_minutes: int = 20,
) -> dict:
    """
    Generate an optimal feeding schedule.

    Algorithm:
    1. Calculate equal interval from first to last (or 24h distribution)
    2. For each proposed feeding time, check against blocked windows
    3. If conflict: shift feeding to before window start (minus buffer)
       or to after window end (plus small gap)
    4. Re-propagate subsequent feedings from adjusted time

    Returns dict with feeding_times (list of HH:MM), intervals, and warnings.
    """
    warnings = []

    first_min = parse_hhmm(first_feeding_time)

    if last_feeding_time:
        last_min = parse_hhmm(last_feeding_time)
        # Handle overnight: last is next day
        if last_min < first_min:
            last_min += 24 * 60
        if num_feedings == 1:
            interval = 0
        else:
            interval = (last_min - first_min) / (num_feedings - 1)
    else:
        # Distribute over 24 hours
        interval = (24 * 60) / num_feedings

    # Generate ideal times
    ideal = []
    for i in range(num_feedings):
        ideal.append(first_min + i * interval)

    if not blocked_windows:
        times = [minutes_to_hhmm(int(m)) for m in ideal]
        intervals = _compute_intervals(ideal)
        return {"feeding_times": times, "intervals_minutes": intervals, "warnings": []}

    # Parse blocked windows to minutes
    parsed_blocks = []
    for bw in blocked_windows:
        try:
            s = parse_hhmm(bw["start"])
            e = parse_hhmm(bw["end"])
            label = bw.get("label", "")
            parsed_blocks.append({"start": s, "end": e, "label": label})
        except (ValueError, KeyError):
            warnings.append(f"Ongeldige blokkade overgeslagen / Invalid blocked window skipped")

    # Adjust each feeding for conflicts
    adjusted = list(ideal)
    for i in range(num_feedings):
        feed_min = adjusted[i]
        shifted = _resolve_conflict(int(feed_min), parsed_blocks, burp_buffer_minutes)
        if shifted != int(feed_min):
            label = _find_conflicting_label(int(feed_min), parsed_blocks)
            warnings.append(
                f"Voeding {i+1} ({minutes_to_hhmm(int(feed_min))}) "
                f"verschoven naar {minutes_to_hhmm(shifted)}"
                + (f" vanwege '{label}'" if label else "")
            )
            # Re-propagate: adjust subsequent feedings from shifted time
            delta = shifted - int(feed_min)
            for j in range(i, num_feedings):
                adjusted[j] = adjusted[j] + delta

    times = [minutes_to_hhmm(int(m)) for m in adjusted]
    intervals = _compute_intervals(adjusted)
    return {"feeding_times": times, "intervals_minutes": intervals, "warnings": warnings}


def _find_conflicting_label(feed_min: int, blocks: List[Dict]) -> str:
    for block in blocks:
        if is_in_window(feed_min, block["start"], block["end"]):
            return block.get("label", "")
    # Also check burp overlap at start
    return ""


def _resolve_conflict(feed_min: int, blocks: List[Dict], burp_buffer: int) -> int:
    """Try to find a non-conflicting time, shifting after the block."""
    MAX_ITER = len(blocks) * 2 + 1
    current = feed_min
    for _ in range(MAX_ITER):
        conflict = _find_conflict(current, blocks, burp_buffer)
        if conflict is None:
            return current
        # Shift to just after the blocking window ends
        current = conflict["end"] + 5  # 5-minute gap after block
    return current  # best we can do


def _find_conflict(feed_min: int, blocks: List[Dict], burp_buffer: int) -> Optional[Dict]:
    """Return the first block that conflicts with a feeding at feed_min."""
    feed_end = feed_min + burp_buffer
    for block in blocks:
        bs, be = block["start"], block["end"]
        # Feeding start is inside block
        if is_in_window(feed_min, bs, be):
            return block
        # Feeding end (burp time) overlaps with block start
        if bs <= feed_end and feed_min < be:
            return block
    return None


def _compute_intervals(times_minutes: List[float]) -> List[int]:
    """Compute intervals in minutes between consecutive feedings."""
    intervals = []
    for i in range(1, len(times_minutes)):
        diff = int(times_minutes[i] - times_minutes[i - 1])
        diff = diff % (24 * 60)  # handle midnight wrap
        intervals.append(diff)
    return intervals
