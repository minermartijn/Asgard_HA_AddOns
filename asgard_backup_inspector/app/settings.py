"""Runtime settings, read from the Home Assistant App options file."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_STALE_HOURS = 1
MAX_STALE_HOURS = 24 * 90
DEFAULT_STALE_HOURS = 48
DEFAULT_GOOGLE_DRIVE_SENSOR = "sensor.backup_state"


@dataclass(frozen=True)
class Settings:
    stale_threshold_hours: int = DEFAULT_STALE_HOURS
    demo_mode: bool = False
    supervisor_token: str | None = None
    supervisor_url: str = "http://supervisor"
    # Ingress only reaches the App from the Supervisor proxy at this address.
    allowed_clients: tuple[str, ...] = ("172.30.32.2",)
    data_dir: str = "/data"
    min_refresh_interval_seconds: float = 10.0
    cache_ttl_seconds: float = 300.0

    # Multi-location / Cloud provider settings
    enable_google_drive: bool = True
    google_drive_sensor: str = DEFAULT_GOOGLE_DRIVE_SENSOR
    core_api_url: str = "http://supervisor/core/api"


def _clamp_hours(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return DEFAULT_STALE_HOURS
    return int(min(MAX_STALE_HOURS, max(MIN_STALE_HOURS, value)))


def load_settings(options_path: str | os.PathLike = "/data/options.json") -> Settings:
    options: dict = {}
    path = Path(options_path)
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                options = loaded
        except (OSError, ValueError):
            logger.warning("Could not read App options; using defaults.")

    allowed_env = os.getenv("ASGARD_ALLOWED_CLIENTS")
    allowed = (
        tuple(c.strip() for c in allowed_env.split(",") if c.strip())
        if allowed_env is not None
        else Settings.allowed_clients
    )

    enable_gdrive_env = os.getenv("ASGARD_ENABLE_GOOGLE_DRIVE")
    if enable_gdrive_env is not None:
        enable_google_drive = enable_gdrive_env.lower() in ("1", "true", "yes")
    elif "enable_google_drive" in options:
        enable_google_drive = options.get("enable_google_drive") is True
    else:
        enable_google_drive = True

    sensor_name = (
        os.getenv("ASGARD_GOOGLE_DRIVE_SENSOR")
        or options.get("google_drive_sensor")
        or DEFAULT_GOOGLE_DRIVE_SENSOR
    )
    if not isinstance(sensor_name, str) or not sensor_name.strip():
        sensor_name = DEFAULT_GOOGLE_DRIVE_SENSOR

    return Settings(
        stale_threshold_hours=_clamp_hours(options.get("stale_threshold_hours", DEFAULT_STALE_HOURS)),
        demo_mode=options.get("demo_mode") is True,
        supervisor_token=os.getenv("SUPERVISOR_TOKEN") or None,
        supervisor_url=os.getenv("ASGARD_SUPERVISOR_URL", "http://supervisor"),
        allowed_clients=allowed,
        data_dir=os.getenv("ASGARD_DATA_DIR", "/data"),
        enable_google_drive=enable_google_drive,
        google_drive_sensor=sensor_name.strip(),
        core_api_url=os.getenv("ASGARD_CORE_API_URL", "http://supervisor/core/api"),
    )
