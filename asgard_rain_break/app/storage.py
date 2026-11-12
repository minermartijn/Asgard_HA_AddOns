"""SQLite persistence layer for ASGARD RainBreak."""

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.models import (
    ActivityType,
    AlertLogRecord,
    AppConfig,
    BreakWindow,
    DiscoveredPerson,
    DiscoveredZone,
    LocationMode,
    SavedLocation,
    ScheduleUrgencyMode,
    UrgencyLevel,
    UserProfile,
)


class Storage:
    def __init__(self, db_path: str = ".data/rain_break.db", default_tz: str = "Europe/Amsterdam", default_pushover_token: str = ""):
        self.db_path = db_path
        self.default_tz = default_tz
        self.default_pushover_token = default_pushover_token
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_locations (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS break_windows (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_history (
                    id TEXT PRIMARY KEY,
                    ts_epoch REAL NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dedup_state (
                    dedup_key TEXT PRIMARY KEY,
                    sent_at REAL NOT NULL
                )
                """
            )
            conn.commit()

        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM app_config WHERE id = 1").fetchone()
            if not row:
                cfg = AppConfig(
                    default_timezone=self.default_tz,
                    pushover_app_token=self.default_pushover_token,
                )
                conn.execute(
                    "INSERT INTO app_config (id, payload) VALUES (1, ?)",
                    (cfg.model_dump_json(),),
                )

            loc_count = conn.execute("SELECT COUNT(*) AS c FROM saved_locations").fetchone()["c"]
            if loc_count == 0:
                default_locs = [
                    SavedLocation(
                        id="loc_home",
                        name="Home",
                        latitude=52.3676,
                        longitude=4.9041,
                        ha_zone_entity="zone.home",
                        enabled=True,
                    ),
                    SavedLocation(
                        id="loc_work",
                        name="Work / Office",
                        latitude=52.0907,
                        longitude=5.1214,
                        ha_zone_entity="zone.work",
                        enabled=True,
                    ),
                ]
                for loc in default_locs:
                    conn.execute(
                        "INSERT INTO saved_locations (id, payload) VALUES (?, ?)",
                        (loc.id, loc.model_dump_json()),
                    )

            usr_count = conn.execute("SELECT COUNT(*) AS c FROM user_profiles").fetchone()["c"]
            if usr_count == 0:
                default_users = [
                    UserProfile(
                        id="usr_primary",
                        name="Martijn",
                        enabled=True,
                        ha_person_entity="person.martijn",
                        location_mode=LocationMode.LIVE_PERSON,
                        fixed_location_id="loc_work",
                        fallback_location_id="loc_home",
                        watched_location_ids=["loc_home", "loc_work"],
                        schedule_mode=ScheduleUrgencyMode.URGENT_WINDOW_ELSE_NEUTRAL,
                        window_start="07:30",
                        window_end="17:30",
                        active_days=[0, 1, 2, 3, 4],
                        default_urgency=UrgencyLevel.URGENT,
                        timezone=self.default_tz,
                        continuous_rain_alerts=True,
                        rain_lead_minutes=20,
                        ha_notify_enabled=True,
                        ha_notify_targets=["notify.mobile_app_mart_s25"],
                        pushover_enabled=False,
                    ),
                    UserProfile(
                        id="usr_secondary",
                        name="Household Member 2",
                        enabled=False,
                        ha_person_entity="person.elize",
                        location_mode=LocationMode.LIVE_PERSON,
                        fixed_location_id="loc_home",
                        fallback_location_id="loc_home",
                        watched_location_ids=["loc_home"],
                        schedule_mode=ScheduleUrgencyMode.ACTIVE_WINDOW_ONLY,
                        window_start="08:00",
                        window_end="21:00",
                        active_days=[0, 1, 2, 3, 4, 5, 6],
                        default_urgency=UrgencyLevel.NEUTRAL,
                        timezone=self.default_tz,
                        continuous_rain_alerts=True,
                        rain_lead_minutes=20,
                        ha_notify_enabled=True,
                        ha_notify_targets=[],
                        pushover_enabled=False,
                    ),
                ]
                for u in default_users:
                    conn.execute(
                        "INSERT INTO user_profiles (id, payload) VALUES (?, ?)",
                        (u.id, u.model_dump_json()),
                    )

            brk_count = conn.execute("SELECT COUNT(*) AS c FROM break_windows").fetchone()["c"]
            if brk_count == 0:
                default_breaks = [
                    BreakWindow(
                        id="brk_morning_1000",
                        user_id="usr_primary",
                        name="Morning Break Walk (10:00)",
                        activity_type=ActivityType.WALK,
                        start_time="10:00",
                        duration_minutes=15,
                        flex_before_minutes=30,
                        flex_after_minutes=30,
                        lead_alert_minutes=25,
                        active_days=[0, 1, 2, 3, 4],
                        urgency_override=UrgencyLevel.URGENT,
                        notify_when_dry=False,
                        enabled=True,
                    ),
                    BreakWindow(
                        id="brk_lunch_1230",
                        user_id="usr_primary",
                        name="Lunch Walk / Bike Ride (12:30)",
                        activity_type=ActivityType.WALK,
                        start_time="12:30",
                        duration_minutes=30,
                        flex_before_minutes=30,
                        flex_after_minutes=30,
                        lead_alert_minutes=25,
                        active_days=[0, 1, 2, 3, 4],
                        urgency_override=UrgencyLevel.URGENT,
                        notify_when_dry=False,
                        enabled=True,
                    ),
                    BreakWindow(
                        id="brk_afternoon_1500",
                        user_id="usr_primary",
                        name="Afternoon Break Walk (15:00)",
                        activity_type=ActivityType.WALK,
                        start_time="15:00",
                        duration_minutes=15,
                        flex_before_minutes=30,
                        flex_after_minutes=30,
                        lead_alert_minutes=25,
                        active_days=[0, 1, 2, 3, 4],
                        urgency_override=UrgencyLevel.URGENT,
                        notify_when_dry=False,
                        enabled=True,
                    ),
                ]
                for b in default_breaks:
                    conn.execute(
                        "INSERT INTO break_windows (id, payload) VALUES (?, ?)",
                        (b.id, b.model_dump_json()),
                    )
            conn.commit()

    # --- AppConfig ---
    def get_config(self) -> AppConfig:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM app_config WHERE id = 1").fetchone()
            if not row:
                return AppConfig(default_timezone=self.default_tz, pushover_app_token=self.default_pushover_token)
            return AppConfig.model_validate_json(row["payload"])

    def save_config(self, cfg: AppConfig) -> AppConfig:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_config (id, payload) VALUES (1, ?)",
                (cfg.model_dump_json(),),
            )
            conn.commit()
        return cfg

    # --- Saved Locations ---
    def list_locations(self) -> List[SavedLocation]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM saved_locations ORDER BY id ASC").fetchall()
            return [SavedLocation.model_validate_json(r["payload"]) for r in rows]

    def get_location(self, loc_id: str) -> Optional[SavedLocation]:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM saved_locations WHERE id = ?", (loc_id,)).fetchone()
            return SavedLocation.model_validate_json(row["payload"]) if row else None

    def save_location(self, loc: SavedLocation) -> SavedLocation:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO saved_locations (id, payload) VALUES (?, ?)",
                (loc.id, loc.model_dump_json()),
            )
            conn.commit()
        return loc

    def delete_location(self, loc_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM saved_locations WHERE id = ?", (loc_id,))
            conn.commit()
            return cur.rowcount > 0

    # --- User Profiles ---
    def list_users(self) -> List[UserProfile]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM user_profiles ORDER BY id ASC").fetchall()
            return [UserProfile.model_validate_json(r["payload"]) for r in rows]

    def get_user(self, user_id: str) -> Optional[UserProfile]:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM user_profiles WHERE id = ?", (user_id,)).fetchone()
            return UserProfile.model_validate_json(row["payload"]) if row else None

    def save_user(self, user: UserProfile) -> UserProfile:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_profiles (id, payload) VALUES (?, ?)",
                (user.id, user.model_dump_json()),
            )
            conn.commit()
        return user

    def delete_user(self, user_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM user_profiles WHERE id = ?", (user_id,))
            conn.commit()
            return cur.rowcount > 0

    # --- Break Windows ---
    def list_breaks(self) -> List[BreakWindow]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM break_windows ORDER BY id ASC").fetchall()
            breaks = [BreakWindow.model_validate_json(r["payload"]) for r in rows]
            return sorted(breaks, key=lambda b: b.start_time)

    def get_break(self, break_id: str) -> Optional[BreakWindow]:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM break_windows WHERE id = ?", (break_id,)).fetchone()
            return BreakWindow.model_validate_json(row["payload"]) if row else None

    def save_break(self, brk: BreakWindow) -> BreakWindow:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO break_windows (id, payload) VALUES (?, ?)",
                (brk.id, brk.model_dump_json()),
            )
            conn.commit()
        return brk

    def delete_break(self, break_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM break_windows WHERE id = ?", (break_id,))
            conn.commit()
            return cur.rowcount > 0

    # --- Sync HA Zones & Persons ---
    def sync_from_ha(self, persons: List[DiscoveredPerson], zones: List[DiscoveredZone]) -> dict:
        added_zones = 0
        updated_zones = 0
        added_users = 0

        existing_locs = {loc.id: loc for loc in self.list_locations()}
        by_zone_entity = {loc.ha_zone_entity: loc for loc in existing_locs.values() if loc.ha_zone_entity}

        for z in zones:
            if z.entity_id in by_zone_entity:
                loc = by_zone_entity[z.entity_id]
                loc.latitude = z.latitude
                loc.longitude = z.longitude
                loc.name = z.name or loc.name
                self.save_location(loc)
                updated_zones += 1
            else:
                slug = z.entity_id.replace("zone.", "loc_")
                if slug in existing_locs:
                    loc = existing_locs[slug]
                    loc.latitude = z.latitude
                    loc.longitude = z.longitude
                    loc.ha_zone_entity = z.entity_id
                    self.save_location(loc)
                    updated_zones += 1
                else:
                    new_loc = SavedLocation(
                        id=slug,
                        name=z.name,
                        latitude=z.latitude,
                        longitude=z.longitude,
                        ha_zone_entity=z.entity_id,
                        enabled=True,
                    )
                    self.save_location(new_loc)
                    added_zones += 1

        existing_users = self.list_users()
        by_person_entity = {u.ha_person_entity: u for u in existing_users if u.ha_person_entity}

        for idx, p in enumerate(persons):
            if p.entity_id in by_person_entity:
                continue
            # Check if one of the default placeholder users matches by name or can be linked
            matched = False
            for u in existing_users:
                if u.name.lower() in p.name.lower() or p.name.lower() in u.name.lower():
                    u.ha_person_entity = p.entity_id
                    u.name = p.name
                    self.save_user(u)
                    by_person_entity[p.entity_id] = u
                    matched = True
                    break
            if not matched:
                slug = p.entity_id.replace("person.", "usr_")
                new_user = UserProfile(
                    id=slug,
                    name=p.name,
                    enabled=(len(existing_users) == 0 and idx == 0),
                    ha_person_entity=p.entity_id,
                    location_mode=LocationMode.LIVE_PERSON,
                    fixed_location_id="loc_home",
                    fallback_location_id="loc_home",
                    watched_location_ids=["loc_home"],
                    timezone=self.default_tz,
                )
                self.save_user(new_user)
                existing_users.append(new_user)
                added_users += 1

        return {
            "added_zones": added_zones,
            "updated_zones": updated_zones,
            "added_users": added_users,
        }

    # --- Alert History & Dedup ---
    def add_alert_log(self, record: AlertLogRecord) -> None:
        ts = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO alert_history (id, ts_epoch, payload) VALUES (?, ?, ?)",
                (record.id, ts, record.model_dump_json()),
            )
            conn.commit()

    def list_alert_history(self, limit: int = 100) -> List[AlertLogRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM alert_history ORDER BY ts_epoch DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [AlertLogRecord.model_validate_json(r["payload"]) for r in rows]

    def clear_alert_history(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM alert_history")
            conn.commit()
            return cur.rowcount

    def is_dedup_active(self, key: str, cooldown_minutes: int) -> bool:
        now = time.time()
        cutoff = now - (cooldown_minutes * 60)
        with self._connect() as conn:
            row = conn.execute("SELECT sent_at FROM dedup_state WHERE dedup_key = ?", (key,)).fetchone()
            if row and row["sent_at"] >= cutoff:
                return True
            return False

    def mark_dedup_sent(self, key: str) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO dedup_state (dedup_key, sent_at) VALUES (?, ?)",
                (key, now),
            )
            conn.commit()
