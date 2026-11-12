"""Configuration settings for ASGARD RainBreak."""

import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "ASGARD RainBreak"
    version: str = "0.2.0"
    demo_mode: bool = False
    default_timezone: str = "Europe/Amsterdam"
    poll_interval_seconds: int = 180
    default_rain_threshold_mm: float = 0.15
    pushover_app_token: str = ""
    supervisor_token: Optional[str] = None
    ha_core_url: str = "http://supervisor/core/api"
    db_path: str = "/data/rain_break.db"
    require_ingress_header: bool = False


def load_settings() -> Settings:
    options_file = Path("/data/options.json")
    data: dict = {}
    if options_file.exists():
        try:
            data = json.loads(options_file.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    supervisor_token = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASSIO_TOKEN")

    demo_mode_env = os.environ.get("ASGARD_DEMO_MODE")
    if demo_mode_env is not None:
        demo_mode = demo_mode_env.lower() in ("1", "true", "yes")
    elif "demo_mode" in data:
        demo_mode = bool(data["demo_mode"])
    else:
        demo_mode = not bool(supervisor_token)

    default_tz = os.environ.get("ASGARD_DEFAULT_TZ") or data.get("default_timezone", "Europe/Amsterdam")
    poll_sec = int(os.environ.get("ASGARD_POLL_SECONDS") or data.get("poll_interval_seconds", 180))
    threshold_mm = float(os.environ.get("ASGARD_RAIN_THRESHOLD_MM") or data.get("default_rain_threshold_mm", 0.15))
    pushover_token = os.environ.get("ASGARD_PUSHOVER_APP_TOKEN") or str(data.get("pushover_app_token") or "")
    db_path = os.environ.get("ASGARD_DB_PATH") or (
        "/data/rain_break.db" if Path("/data").exists() and os.access("/data", os.W_OK) else ".data/rain_break.db"
    )
    require_ingress = os.environ.get("ASGARD_REQUIRE_INGRESS", "0").lower() in ("1", "true", "yes")

    return Settings(
        demo_mode=demo_mode,
        default_timezone=default_tz,
        poll_interval_seconds=poll_sec,
        default_rain_threshold_mm=threshold_mm,
        pushover_app_token=pushover_token,
        supervisor_token=supervisor_token,
        db_path=db_path,
        require_ingress_header=require_ingress,
    )
