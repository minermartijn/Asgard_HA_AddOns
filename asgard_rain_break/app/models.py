"""Data models for ASGARD RainBreak."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class LocationMode(str, Enum):
    LIVE_PERSON = "live_person"
    FIXED_LOCATION = "fixed_location"
    MULTI_LOCATION = "multi_location"


class ScheduleUrgencyMode(str, Enum):
    ALWAYS = "always"
    ACTIVE_WINDOW_ONLY = "active_window_only"
    URGENT_WINDOW_ELSE_NEUTRAL = "urgent_window_else_neutral"


class UrgencyLevel(str, Enum):
    URGENT = "urgent"
    NEUTRAL = "neutral"
    AUTO = "auto"


class WeatherProviderMode(str, Enum):
    AUTO = "auto"
    BUIENRADAR = "buienradar"
    OPEN_METEO = "open_meteo"


class ActivityType(str, Enum):
    WALK = "walk"
    BIKE = "bike"
    RUN = "run"
    BREAK = "break"


class BreakAdviceStatus(str, Enum):
    DRY_ON_SCHEDULE = "dry_on_schedule"
    DRY_BUT_RAIN_SOON_AFTER = "dry_but_rain_soon_after"
    SHIFT_EARLIER_DRY = "shift_earlier_dry"
    SHIFT_LATER_DRY = "shift_later_dry"
    SHIFT_CLEANER_SLOT = "shift_cleaner_slot"
    HEAVY_RAIN_NO_WINDOW = "heavy_rain_no_window"


class SavedLocation(BaseModel):
    id: str
    name: str
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    ha_zone_entity: Optional[str] = None
    enabled: bool = True


class UserProfile(BaseModel):
    id: str
    name: str
    enabled: bool = True
    ha_person_entity: Optional[str] = None
    location_mode: LocationMode = LocationMode.LIVE_PERSON
    fixed_location_id: Optional[str] = None
    fallback_location_id: Optional[str] = None
    watched_location_ids: List[str] = Field(default_factory=list)
    schedule_mode: ScheduleUrgencyMode = ScheduleUrgencyMode.URGENT_WINDOW_ELSE_NEUTRAL
    window_start: str = "07:30"
    window_end: str = "18:00"
    active_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    default_urgency: UrgencyLevel = UrgencyLevel.URGENT
    timezone: str = "Europe/Amsterdam"
    continuous_rain_alerts: bool = True
    rain_lead_minutes: int = Field(default=20, ge=5, le=120)
    ha_notify_enabled: bool = True
    ha_notify_targets: List[str] = Field(default_factory=list)
    pushover_enabled: bool = False
    pushover_user_key: str = ""
    pushover_app_token: str = ""
    pushover_device: str = ""
    pushover_urgent_priority: int = Field(default=1, ge=0, le=2)
    pushover_sound: str = "pushover"


class BreakWindow(BaseModel):
    id: str
    user_id: str
    name: str
    activity_type: ActivityType = ActivityType.WALK
    start_time: str = "10:00"
    duration_minutes: int = Field(default=15, ge=5, le=180)
    flex_before_minutes: int = Field(default=30, ge=0, le=120)
    flex_after_minutes: int = Field(default=30, ge=0, le=120)
    lead_alert_minutes: int = Field(default=25, ge=5, le=120)
    active_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    location_override_id: Optional[str] = None
    urgency_override: UrgencyLevel = UrgencyLevel.AUTO
    notify_when_dry: bool = False
    enabled: bool = True


class AppConfig(BaseModel):
    default_timezone: str = "Europe/Amsterdam"
    weather_provider: WeatherProviderMode = WeatherProviderMode.AUTO
    rain_threshold_mm: float = Field(default=0.15, ge=0.05, le=10.0)
    heavy_rain_threshold_mm: float = Field(default=2.0, ge=0.5, le=25.0)
    pushover_app_token: str = ""
    background_monitoring_enabled: bool = True
    dedup_cooldown_minutes: int = Field(default=30, ge=5, le=240)


class DiscoveredPerson(BaseModel):
    entity_id: str
    name: str
    state: str = "unknown"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy: Optional[float] = None
    source: Optional[str] = None


class DiscoveredZone(BaseModel):
    entity_id: str
    name: str
    latitude: float
    longitude: float
    radius_m: float = 100.0
    icon: str = "mdi:map-marker"


class DiscoveredNotifyAction(BaseModel):
    action: str
    name: str
    description: str = ""
    target_type: str = "service"
    preferred_alternative: Optional[str] = None


class RainPoint(BaseModel):
    timestamp_iso: str
    time_label: str
    minutes_from_now: int
    mm_per_hour: float
    probability_pct: int = 0
    source: str = "buienradar"


class LocationForecast(BaseModel):
    location_id: str
    location_name: str
    latitude: float
    longitude: float
    source_used: str
    fetched_at: str
    is_currently_raining: bool
    current_mm_h: float
    next_rain_in_minutes: Optional[int] = None
    next_rain_time_label: Optional[str] = None
    dry_in_minutes: Optional[int] = None
    peak_mm_h_next_2h: float = 0.0
    summary_text: str = ""
    points: List[RainPoint] = Field(default_factory=list)


class SlotCandidate(BaseModel):
    start_time: str
    end_time: str
    shift_minutes: int
    max_mm_h: float
    avg_mm_h: float
    wet_minutes: int
    is_dry: bool


class BreakEvaluation(BaseModel):
    break_id: str
    break_name: str
    user_id: str
    user_name: str
    activity_type: ActivityType
    location_id: str
    location_name: str
    location_source: str = "fixed"
    latitude: float
    longitude: float
    planned_start: str
    planned_end: str
    duration_minutes: int
    flex_before_minutes: int
    flex_after_minutes: int
    status: BreakAdviceStatus
    effective_urgency: str
    schedule_allowed: bool
    schedule_reason: str
    should_notify: bool
    headline: str
    advice_text: str
    planned_slot: SlotCandidate
    recommended_slot: SlotCandidate
    all_candidates: List[SlotCandidate] = Field(default_factory=list)


class AlertLogRecord(BaseModel):
    id: str
    timestamp: str
    user_id: str
    user_name: str
    break_id: Optional[str] = None
    break_name: Optional[str] = None
    location_name: str
    alert_type: str
    urgency: str
    channel: str
    target: str
    status: str
    title: str
    message_preview: str
    detail: str = ""
