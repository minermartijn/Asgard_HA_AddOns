"""High-resolution precipitation forecast client (Buienradar 5-min + Open-Meteo 15-min/hourly)."""

from datetime import datetime, timedelta, timezone
import logging
import math
import time
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx

from app.models import LocationForecast, RainPoint, WeatherProviderMode

logger = logging.getLogger("asgard_rain_break.weather")


def buienradar_raw_to_mm_h(raw_value: int) -> float:
    """Convert Buienradar 0-255 rain value to mm/h using the official logarithmic formula."""
    if raw_value <= 0:
        return 0.0
    mm = 10.0 ** ((raw_value - 109.0) / 32.0)
    return round(mm if mm >= 0.03 else 0.0, 2)


def is_benelux_coords(lat: float, lon: float) -> bool:
    """Return True if coordinates fall within the Buienradar Benelux radar coverage area."""
    return 49.0 <= lat <= 54.5 and 2.5 <= lon <= 7.6


def parse_buienradar_text(
    raw_text: str,
    now_local: datetime,
) -> List[RainPoint]:
    """Parse Buienradar raintext lines ('077|10:05') into RainPoint objects."""
    points: List[RainPoint] = []
    lines = [ln.strip() for ln in (raw_text or "").splitlines() if "|" in ln]
    base_minute = now_local.replace(second=0, microsecond=0)
    prev_dt: Optional[datetime] = None

    for idx, line in enumerate(lines):
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        try:
            raw_val = int(parts[0].strip())
            hh_str, mm_str = parts[1].strip().split(":", 1)
            hh, mm = int(hh_str), int(mm_str)
        except ValueError:
            continue

        candidate = base_minute.replace(hour=hh, minute=mm)
        if prev_dt is not None and candidate < prev_dt - timedelta(hours=12):
            candidate += timedelta(days=1)
        elif idx == 0 and candidate < base_minute - timedelta(hours=12):
            candidate += timedelta(days=1)
        elif idx == 0 and candidate > base_minute + timedelta(hours=12):
            candidate -= timedelta(days=1)

        prev_dt = candidate
        mm_h = buienradar_raw_to_mm_h(raw_val)
        mins_from_now = int(round((candidate - now_local).total_seconds() / 60.0))
        prob = 0 if mm_h == 0 else min(98, max(25, int(35 + mm_h * 20)))

        points.append(
            RainPoint(
                timestamp_iso=candidate.isoformat(),
                time_label=candidate.strftime("%H:%M"),
                minutes_from_now=max(0, mins_from_now),
                mm_per_hour=mm_h,
                probability_pct=prob,
                source="buienradar",
            )
        )
    return points


def build_summary_from_points(
    location_id: str,
    location_name: str,
    lat: float,
    lon: float,
    source_used: str,
    points: List[RainPoint],
    rain_threshold_mm: float,
    now_local: datetime,
) -> LocationForecast:
    if not points:
        return LocationForecast(
            location_id=location_id,
            location_name=location_name,
            latitude=lat,
            longitude=lon,
            source_used=source_used,
            fetched_at=now_local.isoformat(),
            is_currently_raining=False,
            current_mm_h=0.0,
            summary_text="No precipitation data available.",
            points=[],
        )

    near_points = [p for p in points if 0 <= p.minutes_from_now <= 125] or points[:25]
    current_pt = near_points[0]
    current_mm = current_pt.mm_per_hour
    currently_raining = current_mm >= rain_threshold_mm
    peak_2h = max((p.mm_per_hour for p in near_points), default=0.0)

    next_rain_min: Optional[int] = None
    next_rain_label: Optional[str] = None
    dry_in_min: Optional[int] = None

    if currently_raining:
        for p in near_points[1:]:
            if p.mm_per_hour < rain_threshold_mm:
                dry_in_min = p.minutes_from_now
                break
        if dry_in_min is not None:
            summary = f"Raining now ({current_mm:.1f} mm/h) — expected to become dry in ~{dry_in_min} min."
        else:
            summary = f"Raining now ({current_mm:.1f} mm/h) — rain continues over the next 2 hours (peak {peak_2h:.1f} mm/h)."
    else:
        for p in near_points:
            if p.mm_per_hour >= rain_threshold_mm:
                next_rain_min = p.minutes_from_now
                next_rain_label = p.time_label
                break
        if next_rain_min is not None:
            summary = f"Dry now — rain expected in {next_rain_min} min (around {next_rain_label}, peak {peak_2h:.1f} mm/h)."
        else:
            summary = "Completely dry for the next 2 hours (0.0 mm/h)."

    return LocationForecast(
        location_id=location_id,
        location_name=location_name,
        latitude=lat,
        longitude=lon,
        source_used=source_used,
        fetched_at=now_local.isoformat(),
        is_currently_raining=currently_raining,
        current_mm_h=current_mm,
        next_rain_in_minutes=next_rain_min,
        next_rain_time_label=next_rain_label,
        dry_in_minutes=dry_in_min,
        peak_mm_h_next_2h=round(peak_2h, 2),
        summary_text=summary,
        points=points,
    )


class WeatherService:
    """Fetches and caches high-resolution precipitation timelines."""

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.demo_scenario: str = "workday_break_rain"
        self._cache: Dict[Tuple[float, float, str], Tuple[float, List[RainPoint], str]] = {}
        self.cache_ttl_seconds = 120.0

    def set_demo_scenario(self, scenario: str) -> None:
        self.demo_scenario = scenario
        self._cache.clear()

    def generate_demo_points(
        self,
        now_local: datetime,
        scenario: Optional[str] = None,
    ) -> Tuple[List[RainPoint], str]:
        scen = scenario or self.demo_scenario
        base = now_local.replace(second=0, microsecond=0)
        base = base - timedelta(minutes=base.minute % 5)

        # Cover from 07:00 today through +10 hours so both immediate radar and scheduled workday breaks (10:00, 12:30, 15:00) have rich data
        day_start = base.replace(hour=7, minute=0)
        start_dt = min(base, day_start)
        end_dt = max(base + timedelta(hours=6), base.replace(hour=18, minute=0))

        points: List[RainPoint] = []
        cur = start_dt
        while cur <= end_dt:
            mins_from_now = int(round((cur - now_local).total_seconds() / 60.0))
            hh_mm = cur.hour * 60 + cur.minute
            mm_h = 0.0
            prob = 5

            if scen == "workday_break_rain":
                # Exact user story:
                # 10:00 - 10:20 has heavy rain (2.4 mm/h), while 09:30 - 10:00 is completely dry!
                # 12:30 - 12:45 has rain (1.8 mm/h), while 12:45 - 13:20 is completely dry!
                # 15:00 - 15:15 is completely dry!
                if 10 * 60 <= hh_mm <= 10 * 60 + 20:
                    mm_h = 2.4 if hh_mm in (605, 610) else 1.6
                    prob = 90
                elif 12 * 60 + 25 <= hh_mm <= 12 * 60 + 40:
                    mm_h = 1.9
                    prob = 85
                elif 15 <= mins_from_now <= 30:
                    # Also show a shower on the immediate 2h radar if not already covered
                    mm_h = max(mm_h, 1.8)
                    prob = 85
            elif scen == "imminent_shower":
                if 10 <= mins_from_now <= 35:
                    mm_h = 2.8 if 15 <= mins_from_now <= 25 else 1.2
                    prob = 92
                if 10 * 60 <= hh_mm <= 10 * 60 + 15:
                    mm_h = max(mm_h, 2.2)
                    prob = 90
            elif scen == "heavy_storm":
                if -30 <= mins_from_now <= 180 or (9 * 60 + 30 <= hh_mm <= 11 * 60):
                    mm_h = 3.6
                    prob = 98
            elif scen == "all_clear":
                mm_h = 0.0
                prob = 0

            points.append(
                RainPoint(
                    timestamp_iso=cur.isoformat(),
                    time_label=cur.strftime("%H:%M"),
                    minutes_from_now=mins_from_now,
                    mm_per_hour=round(mm_h, 2),
                    probability_pct=prob,
                    source=f"demo:{scen}",
                )
            )
            cur += timedelta(minutes=5)

        return points, f"Demo Radar ({scen})"

    async def get_forecast(
        self,
        location_id: str,
        location_name: str,
        latitude: float,
        longitude: float,
        provider_mode: WeatherProviderMode = WeatherProviderMode.AUTO,
        rain_threshold_mm: float = 0.15,
        tz_name: str = "Europe/Amsterdam",
        force_refresh: bool = False,
        now_override: Optional[datetime] = None,
    ) -> LocationForecast:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("Europe/Amsterdam")

        now_local = now_override.astimezone(tz) if now_override else datetime.now(tz)

        if self.demo_mode:
            pts, src = self.generate_demo_points(now_local)
            return build_summary_from_points(
                location_id, location_name, latitude, longitude, src, pts, rain_threshold_mm, now_local
            )

        cache_key = (round(latitude, 3), round(longitude, 3), provider_mode.value)
        now_ts = time.time()
        if not force_refresh and cache_key in self._cache:
            cached_at, cached_pts, cached_src = self._cache[cache_key]
            if now_ts - cached_at < self.cache_ttl_seconds:
                return build_summary_from_points(
                    location_id,
                    location_name,
                    latitude,
                    longitude,
                    cached_src,
                    cached_pts,
                    rain_threshold_mm,
                    now_local,
                )

        buien_pts: List[RainPoint] = []
        meteo_pts: List[RainPoint] = []
        sources_used: List[str] = []

        use_buien = provider_mode == WeatherProviderMode.BUIENRADAR or (
            provider_mode == WeatherProviderMode.AUTO and is_benelux_coords(latitude, longitude)
        )
        use_meteo = provider_mode in (WeatherProviderMode.AUTO, WeatherProviderMode.OPEN_METEO)

        async with httpx.AsyncClient(timeout=8.0) as client:
            if use_buien:
                try:
                    b_url = f"https://gpsgadget.buienradar.nl/data/raintext/?lat={latitude:.4f}&lon={longitude:.4f}"
                    resp = await client.get(b_url)
                    if resp.status_code == 200 and "|" in resp.text:
                        buien_pts = parse_buienradar_text(resp.text, now_local)
                        if buien_pts:
                            sources_used.append("Buienradar 5m")
                except Exception as exc:
                    logger.warning("Buienradar fetch failed for (%s, %s): %s", latitude, longitude, exc)

            if use_meteo or not buien_pts:
                try:
                    m_url = (
                        "https://api.open-meteo.com/v1/forecast"
                        f"?latitude={latitude:.4f}&longitude={longitude:.4f}"
                        "&minutely_15=precipitation,rain"
                        "&hourly=precipitation,precipitation_probability"
                        "&forecast_days=2"
                        f"&timezone={tz_name}"
                    )
                    resp = await client.get(m_url)
                    if resp.status_code == 200:
                        meteo_pts = self._parse_open_meteo(resp.json(), now_local, tz)
                        if meteo_pts:
                            sources_used.append("Open-Meteo")
                except Exception as exc:
                    logger.warning("Open-Meteo fetch failed for (%s, %s): %s", latitude, longitude, exc)

        merged = self._merge_points(buien_pts, meteo_pts)
        source_label = " + ".join(sources_used) if sources_used else "Unavailable"
        if merged:
            self._cache[cache_key] = (now_ts, merged, source_label)

        return build_summary_from_points(
            location_id,
            location_name,
            latitude,
            longitude,
            source_label,
            merged,
            rain_threshold_mm,
            now_local,
        )

    def _parse_open_meteo(
        self,
        data: dict,
        now_local: datetime,
        tz: ZoneInfo,
    ) -> List[RainPoint]:
        points: List[RainPoint] = []
        m15 = data.get("minutely_15") or {}
        times = m15.get("time") or []
        precip = m15.get("precipitation") or []

        hourly = data.get("hourly") or {}
        h_times = hourly.get("time") or []
        h_probs = hourly.get("precipitation_probability") or []
        prob_by_hour: Dict[str, int] = {}
        for ht, hp in zip(h_times, h_probs):
            if ht and hp is not None:
                prob_by_hour[ht[:13]] = int(hp)

        for t_str, p_val in zip(times, precip):
            try:
                dt = datetime.fromisoformat(t_str).replace(tzinfo=tz)
            except ValueError:
                continue
            diff_min = (dt - now_local).total_seconds() / 60.0
            if diff_min < -60 or diff_min > 12 * 60:
                continue
            # precipitation in minutely_15 is mm in 15 min -> multiply by 4 for mm/h rate
            mm_15 = float(p_val or 0.0)
            mm_h = round(mm_15 * 4.0, 2)
            prob = prob_by_hour.get(t_str[:13], 0 if mm_h == 0 else 60)

            # Expand each 15-minute block into three 5-minute points for seamless break window evaluation
            for offset in (0, 5, 10):
                sub_dt = dt + timedelta(minutes=offset)
                mins_now = int(round((sub_dt - now_local).total_seconds() / 60.0))
                points.append(
                    RainPoint(
                        timestamp_iso=sub_dt.isoformat(),
                        time_label=sub_dt.strftime("%H:%M"),
                        minutes_from_now=mins_now,
                        mm_per_hour=mm_h,
                        probability_pct=prob,
                        source="open_meteo",
                    )
                )
        return points

    def _merge_points(self, buien_pts: List[RainPoint], meteo_pts: List[RainPoint]) -> List[RainPoint]:
        if buien_pts and not meteo_pts:
            return buien_pts
        if meteo_pts and not buien_pts:
            return meteo_pts
        if not buien_pts and not meteo_pts:
            return []

        by_time: Dict[str, RainPoint] = {}
        for mp in meteo_pts:
            key = mp.timestamp_iso[:16]
            by_time[key] = mp
        # Buienradar 5-min radar takes precedence for the immediate 2-hour window
        for bp in buien_pts:
            key = bp.timestamp_iso[:16]
            by_time[key] = bp

        merged = sorted(by_time.values(), key=lambda p: p.timestamp_iso)
        return merged
