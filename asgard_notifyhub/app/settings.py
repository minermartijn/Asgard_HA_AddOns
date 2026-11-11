"""Configuration settings loaded from Home Assistant /data/options.json and environment."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


DEFAULT_OPTIONS_PATH = Path("/data/options.json")
DEFAULT_DATA_DIR = Path("/data")
DEFAULT_SUPERVISOR_PROXY = "172.30.32.0/23,172.30.32.2,127.0.0.1"


class Settings(BaseModel):
    supervisor_token: Optional[str] = None
    supervisor_url: str = "http://supervisor"
    core_api_url: str = "http://supervisor/core/api"
    data_dir: Path = DEFAULT_DATA_DIR
    allowed_source_ips: str = DEFAULT_SUPERVISOR_PROXY
    demo_mode: bool = False
    default_timezone: str = "Europe/Amsterdam"
    dedup_window_seconds: int = 300
    retention_days: int = 30
    min_refresh_interval_seconds: float = 5.0

    @property
    def db_path(self) -> Path:
        return self.data_dir / "notifyhub.db"


def load_settings(options_path: Optional[Path] = None) -> Settings:
    path = options_path or DEFAULT_OPTIONS_PATH
    raw_options: dict = {}
    if path.exists():
        try:
            raw_options = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raw_options = {}

    token = os.environ.get("SUPERVISOR_TOKEN") or raw_options.get("supervisor_token")
    core_url = os.environ.get("CORE_API_URL") or raw_options.get("core_api_url") or "http://supervisor/core/api"
    data_dir_env = os.environ.get("DATA_DIR")
    if data_dir_env:
        data_dir = Path(data_dir_env)
    else:
        # If running inside HA container, /data exists and is writable
        # In local testing or development, fallback to workspace .data if /data is not accessible
        data_dir = DEFAULT_DATA_DIR
        try:
            if not data_dir.exists():
                data_dir.mkdir(parents=True, exist_ok=True)
            elif not os.access(data_dir, os.W_OK):
                raise PermissionError("not writable")
        except (PermissionError, OSError):
            data_dir = Path(__file__).resolve().parents[1] / ".data"
            data_dir.mkdir(parents=True, exist_ok=True)

    allowed_ips = os.environ.get("ALLOWED_SOURCE_IPS") or raw_options.get("allowed_source_ips") or DEFAULT_SUPERVISOR_PROXY
    demo = bool(raw_options.get("demo_mode", False) or os.environ.get("DEMO_MODE", "").lower() in ("true", "1", "yes"))
    tz = str(raw_options.get("default_timezone", os.environ.get("TZ", "Europe/Amsterdam")))
    dedup = int(raw_options.get("dedup_window_seconds", 300))
    retention = int(raw_options.get("retention_days", 30))

    return Settings(
        supervisor_token=token,
        core_api_url=core_url,
        data_dir=data_dir,
        allowed_source_ips=allowed_ips,
        demo_mode=demo,
        default_timezone=tz,
        dedup_window_seconds=dedup,
        retention_days=retention,
    )
