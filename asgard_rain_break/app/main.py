"""FastAPI application and background monitoring engine for ASGARD RainBreak."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import ipaddress
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import __version__
from app.ha_client import HomeAssistantClient, is_allowed_notify_action, resolve_user_target_locations
from app.models import (
    ActivityType,
    AppConfig,
    BreakAdviceStatus,
    BreakEvaluation,
    BreakWindow,
    DiscoveredNotifyAction,
    DiscoveredPerson,
    DiscoveredZone,
    LocationForecast,
    LocationMode,
    LocationRequirementMode,
    SavedLocation,
    ScheduleUrgencyMode,
    UrgencyLevel,
    UserProfile,
)
from app.notifier import NotificationDispatcher, PushoverClient
from app.optimizer import evaluate_break_window, evaluate_user_schedule, parse_hhmm
from app.settings import Settings, load_settings
from app.storage import Storage
from app.weather import WeatherService

logger = logging.getLogger("asgard_rain_break.main")

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_HTML = BASE_DIR / "frontend" / "index.html"
STATIC_DIR = BASE_DIR / "static"

TRUSTED_SUPERVISOR_NETS = [
    ipaddress.ip_network("172.30.32.0/23"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
]


def is_trusted_ingress_peer(host: Optional[str]) -> bool:
    if not host:
        return False
    if host == "testclient":
        return True
    try:
        ip = ipaddress.ip_address(host)
        return any(ip in net for net in TRUSTED_SUPERVISOR_NETS)
    except ValueError:
        return False


def validate_iana_timezone(tz_name: str) -> str:
    cleaned = (tz_name or "").strip() or "Europe/Amsterdam"
    try:
        ZoneInfo(cleaned)
        return cleaned
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid IANA timezone '{cleaned}': {exc}")


class TogglePayload(BaseModel):
    enabled: bool


class ImportHaLocationPayload(BaseModel):
    name: str
    latitude: float
    longitude: float
    ha_zone_entity: Optional[str] = None
    role: Optional[str] = None  # "work", "home", or None
    user_id: Optional[str] = None


class PresetBreaksPayload(BaseModel):
    user_id: str
    preset: str = "workday_3_breaks"


class TestNotifyPayload(BaseModel):
    user_id: str
    urgency: str = "urgent"
    custom_message: Optional[str] = None


class ScenarioPayload(BaseModel):
    scenario: str


class EvaluateRunPayload(BaseModel):
    break_id: Optional[str] = None
    user_id: Optional[str] = None
    send_notifications: bool = False
    ignore_dedup: bool = False


def create_app(custom_settings: Optional[Settings] = None) -> FastAPI:
    settings = custom_settings or load_settings()
    storage = Storage(
        db_path=settings.db_path,
        default_tz=settings.default_timezone,
        default_pushover_token=settings.pushover_app_token,
    )
    ha_client = HomeAssistantClient(
        base_url=settings.ha_core_url,
        token=settings.supervisor_token,
        demo_mode=settings.demo_mode,
    )
    pushover_client = PushoverClient(demo_mode=settings.demo_mode)
    weather_service = WeatherService(demo_mode=settings.demo_mode)
    dispatcher = NotificationDispatcher(
        storage=storage,
        ha_client=ha_client,
        pushover_client=pushover_client,
    )

    state_cache = {
        "persons": [],
        "zones": [],
        "notify_actions": [],
        "ha_connected": False,
        "ha_status_text": "Checking...",
    }

    async def refresh_discovery() -> None:
        ok, msg = await ha_client.check_connection()
        persons, zones, actions = await ha_client.discover_all()
        state_cache["ha_connected"] = ok
        state_cache["ha_status_text"] = msg
        state_cache["persons"] = persons
        state_cache["zones"] = zones
        state_cache["notify_actions"] = actions

    async def build_all_forecasts_and_evaluations(
        force_refresh: bool = False,
    ) -> Tuple[List[LocationForecast], List[BreakEvaluation]]:
        cfg = storage.get_config()
        locs = storage.list_locations()
        users = storage.list_users()
        breaks = storage.list_breaks()
        persons: List[DiscoveredPerson] = state_cache["persons"]

        forecasts_by_key: Dict[str, LocationForecast] = {}
        ordered_forecasts: List[LocationForecast] = []

        # 1. Forecasts for active users using live_person location mode (Placed FIRST in ordered list)
        for usr in users:
            if not usr.enabled:
                continue
            resolved = resolve_user_target_locations(usr, locs, persons)
            for lid, lname, lat, lon, src in resolved:
                if lid not in forecasts_by_key:
                    fc = await weather_service.get_forecast(
                        location_id=lid,
                        location_name=lname,
                        latitude=lat,
                        longitude=lon,
                        provider_mode=cfg.weather_provider,
                        rain_threshold_mm=cfg.rain_threshold_mm,
                        tz_name=usr.timezone or cfg.default_timezone,
                        force_refresh=force_refresh,
                    )
                    forecasts_by_key[lid] = fc
                    ordered_forecasts.append(fc)

        # 2. Forecasts for all enabled saved locations
        for loc in locs:
            if not loc.enabled:
                continue
            if loc.id not in forecasts_by_key:
                fc = await weather_service.get_forecast(
                    location_id=loc.id,
                    location_name=loc.name,
                    latitude=loc.latitude,
                    longitude=loc.longitude,
                    provider_mode=cfg.weather_provider,
                    rain_threshold_mm=cfg.rain_threshold_mm,
                    tz_name=cfg.default_timezone,
                    force_refresh=force_refresh,
                )
                forecasts_by_key[loc.id] = fc
                ordered_forecasts.append(fc)

        # 3. Evaluate all break windows (with location geofence checking)
        user_by_id = {u.id: u for u in users}
        loc_by_id = {l.id: l for l in locs}
        evaluations: List[BreakEvaluation] = []
        for brk in breaks:
            usr = user_by_id.get(brk.user_id) or (users[0] if users else None)
            if not usr:
                continue
            resolved = resolve_user_target_locations(
                usr,
                locs,
                persons,
                override_location_id=brk.location_override_id,
            )
            lid, lname, lat, lon, src = resolved[0]
            fc = forecasts_by_key.get(lid)
            if not fc:
                fc = await weather_service.get_forecast(
                    location_id=lid,
                    location_name=lname,
                    latitude=lat,
                    longitude=lon,
                    provider_mode=cfg.weather_provider,
                    rain_threshold_mm=cfg.rain_threshold_mm,
                    tz_name=usr.timezone or cfg.default_timezone,
                    force_refresh=force_refresh,
                )
                forecasts_by_key[lid] = fc
                ordered_forecasts.append(fc)

            person_obj = next((p for p in persons if p.entity_id == usr.ha_person_entity), None)
            req_loc = loc_by_id.get(brk.required_location_id) if brk.required_location_id else None

            ev = evaluate_break_window(
                brk=brk,
                user=usr,
                forecast=fc,
                rain_threshold_mm=cfg.rain_threshold_mm,
                location_source=src,
                current_person=person_obj,
                required_location=req_loc,
            )
            evaluations.append(ev)

        return ordered_forecasts, evaluations

    async def run_monitoring_cycle(
        target_break_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        send_notifications: bool = True,
        ignore_dedup: bool = False,
        manual_trigger: bool = False,
    ) -> dict:
        cfg = storage.get_config()
        forecasts, evaluations = await build_all_forecasts_and_evaluations(force_refresh=manual_trigger)
        users = {u.id: u for u in storage.list_users()}
        breaks = {b.id: b for b in storage.list_breaks()}
        sent_records = []

        for ev in evaluations:
            if target_break_id and ev.break_id != target_break_id:
                continue
            if target_user_id and ev.user_id != target_user_id:
                continue

            usr = users.get(ev.user_id)
            brk = breaks.get(ev.break_id)
            if not usr or not brk:
                continue

            if not manual_trigger:
                if not usr.enabled or not brk.enabled:
                    continue
                if not ev.should_notify:
                    continue

                # Check if current time is within lead_alert_minutes before earliest window through planned_end
                try:
                    tz = ZoneInfo(usr.timezone or cfg.default_timezone)
                except Exception:
                    tz = ZoneInfo("Europe/Amsterdam")
                now_dt = datetime.now(tz)
                if now_dt.weekday() not in (brk.active_days or []):
                    continue
                cur_min = now_dt.hour * 60 + now_dt.minute
                earliest_min = parse_hhmm(brk.start_time) - brk.flex_before_minutes - brk.lead_alert_minutes
                latest_min = parse_hhmm(brk.start_time) + brk.duration_minutes
                if not (earliest_min <= cur_min <= latest_min):
                    continue

            if send_notifications:
                dedup_key = f"brk:{ev.break_id}:{ev.status.value}:{ev.recommended_slot.start_time}"
                if not ignore_dedup and storage.is_dedup_active(dedup_key, cfg.dedup_cooldown_minutes):
                    continue
                title = f"RainBreak · {brk.name}: {ev.headline}"
                recs = await dispatcher.dispatch_for_user(
                    user=usr,
                    config=cfg,
                    title=title,
                    message=ev.advice_text,
                    urgency=ev.effective_urgency,
                    location_name=ev.location_name,
                    alert_type="break_advice",
                    break_id=brk.id,
                    break_name=brk.name,
                )
                if any(r.status == "submitted" for r in recs):
                    storage.mark_dedup_sent(dedup_key)
                sent_records.extend(recs)

        # Also check continuous imminent rain alerts for enabled users when running automatic cycle
        if send_notifications and not target_break_id:
            fc_by_id = {f.location_id: f for f in forecasts}
            for usr in users.values():
                if target_user_id and usr.id != target_user_id:
                    continue
                if not usr.enabled or not usr.continuous_rain_alerts:
                    continue
                allowed, eff_urg, _ = evaluate_user_schedule(usr)
                if not allowed:
                    continue
                resolved = resolve_user_target_locations(usr, storage.list_locations(), state_cache["persons"])
                for lid, lname, _, _, _ in resolved:
                    fc = fc_by_id.get(lid)
                    if not fc:
                        continue
                    if (
                        not fc.is_currently_raining
                        and fc.next_rain_in_minutes is not None
                        and 0 < fc.next_rain_in_minutes <= usr.rain_lead_minutes
                    ):
                        dedup_key = f"rain:{usr.id}:{lid}:{fc.next_rain_time_label}"
                        if not ignore_dedup and storage.is_dedup_active(dedup_key, cfg.dedup_cooldown_minutes):
                            continue
                        title = f"☔ Rain starting in {fc.next_rain_in_minutes} min at {lname}"
                        msg = (
                            f"Rain is expected around {fc.next_rain_time_label} at {lname} "
                            f"(peak {fc.peak_mm_h_next_2h:.1f} mm/h in the next 2 hours)."
                        )
                        recs = await dispatcher.dispatch_for_user(
                            user=usr,
                            config=cfg,
                            title=title,
                            message=msg,
                            urgency=eff_urg,
                            location_name=lname,
                            alert_type="imminent_rain",
                        )
                        if any(r.status == "submitted" for r in recs):
                            storage.mark_dedup_sent(dedup_key)
                        sent_records.extend(recs)

        return {
            "evaluations": [e.model_dump() for e in evaluations],
            "records": [r.model_dump() for r in sent_records],
        }

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        await refresh_discovery()
        stop_event = asyncio.Event()

        async def poll_loop():
            while not stop_event.is_set():
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=max(30, settings.poll_interval_seconds))
                except asyncio.TimeoutError:
                    try:
                        cfg = storage.get_config()
                        if cfg.background_monitoring_enabled:
                            await refresh_discovery()
                            await run_monitoring_cycle(send_notifications=True, manual_trigger=False)
                    except Exception as exc:
                        logger.warning("Background poll error: %s", exc)

        bg_task = asyncio.create_task(poll_loop())
        yield
        stop_event.set()
        bg_task.cancel()

    app = FastAPI(
        title="ASGARD RainBreak",
        version=__version__,
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.storage = storage
    app.state.ha_client = ha_client
    app.state.pushover_client = pushover_client
    app.state.weather_service = weather_service
    app.state.dispatcher = dispatcher

    @app.middleware("http")
    async def ingress_guard_middleware(request: Request, call_next):
        if settings.require_ingress_header:
            peer_host = request.client.host if request.client else None
            ingress_path = request.headers.get("X-Ingress-Path")
            if not ingress_path or not is_trusted_ingress_peer(peer_host):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Direct access forbidden; use Home Assistant Supervisor Ingress."},
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    @app.get("", response_class=HTMLResponse, include_in_schema=False)
    async def serve_index(request: Request):
        html = FRONTEND_HTML.read_text(encoding="utf-8")
        ingress_path = request.headers.get("X-Ingress-Path", "").rstrip("/")
        if ingress_path:
            base_tag = f'<base href="{ingress_path}/" />'
            html = html.replace("<head>", f"<head>\n  {base_tag}", 1)
        return HTMLResponse(content=html)

    @app.get("/api/health")
    async def get_health():
        cfg = storage.get_config()
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": __version__,
            "demo_mode": settings.demo_mode,
            "demo_scenario": weather_service.demo_scenario if settings.demo_mode else None,
            "ha_connected": state_cache["ha_connected"],
            "ha_status_text": state_cache["ha_status_text"],
            "default_timezone": cfg.default_timezone,
        }

    @app.get("/api/overview")
    async def get_overview(refresh: bool = False):
        if refresh or not state_cache["persons"]:
            await refresh_discovery()
        cfg = storage.get_config()
        forecasts, evaluations = await build_all_forecasts_and_evaluations(force_refresh=refresh)
        return {
            "version": __version__,
            "demo_mode": settings.demo_mode,
            "demo_scenario": weather_service.demo_scenario,
            "ha_connected": state_cache["ha_connected"],
            "ha_status_text": state_cache["ha_status_text"],
            "config": cfg.model_dump(),
            "discovered": {
                "persons": [p.model_dump() for p in state_cache["persons"]],
                "zones": [z.model_dump() for z in state_cache["zones"]],
                "notify_actions": [a.model_dump() for a in state_cache["notify_actions"]],
            },
            "locations": [loc.model_dump() for loc in storage.list_locations()],
            "users": [u.model_dump() for u in storage.list_users()],
            "breaks": [b.model_dump() for b in storage.list_breaks()],
            "forecasts": [f.model_dump() for f in forecasts],
            "break_evaluations": [e.model_dump() for e in evaluations],
            "recent_alerts": [r.model_dump() for r in storage.list_alert_history(limit=30)],
        }

    @app.post("/api/ha/sync")
    async def sync_ha_entities():
        await refresh_discovery()
        sync_result = storage.sync_from_ha(
            persons=state_cache["persons"],
            zones=state_cache["zones"],
        )
        return {
            "status": "ok",
            "sync": sync_result,
            "persons_count": len(state_cache["persons"]),
            "zones_count": len(state_cache["zones"]),
            "notify_actions_count": len(state_cache["notify_actions"]),
        }

    @app.get("/api/config")
    async def get_config_endpoint():
        return storage.get_config().model_dump()

    @app.post("/api/config")
    async def save_config_endpoint(payload: AppConfig):
        payload.default_timezone = validate_iana_timezone(payload.default_timezone)
        saved = storage.save_config(payload)
        return saved.model_dump()

    # --- Locations CRUD ---
    @app.get("/api/locations")
    async def list_locations_endpoint():
        return {"locations": [loc.model_dump() for loc in storage.list_locations()]}

    @app.post("/api/locations")
    async def save_location_endpoint(loc: SavedLocation):
        if not loc.id.strip():
            loc.id = f"loc_{uuid.uuid4().hex[:8]}"
        if not loc.name.strip():
            raise HTTPException(status_code=400, detail="Location name cannot be empty.")
        saved = storage.save_location(loc)
        return saved.model_dump()

    @app.post("/api/locations/import-ha")
    async def import_ha_location_endpoint(payload: ImportHaLocationPayload):
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Location name cannot be empty.")

        slug = (
            payload.ha_zone_entity.replace("zone.", "loc_").replace("person.", "loc_")
            if payload.ha_zone_entity
            else f"loc_{uuid.uuid4().hex[:8]}"
        )

        loc = SavedLocation(
            id=slug,
            name=clean_name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            ha_zone_entity=payload.ha_zone_entity,
            enabled=True,
        )
        saved = storage.save_location(loc)

        # If user specified role == "work" or "home", update user profile
        if payload.user_id:
            usr = storage.get_user(payload.user_id)
            if usr:
                if payload.role == "work":
                    usr.fixed_location_id = saved.id
                    if saved.id not in usr.watched_location_ids:
                        usr.watched_location_ids.append(saved.id)
                    storage.save_user(usr)
                elif payload.role == "home":
                    usr.fallback_location_id = saved.id
                    if saved.id not in usr.watched_location_ids:
                        usr.watched_location_ids.append(saved.id)
                    storage.save_user(usr)

        return saved.model_dump()

    @app.delete("/api/locations/{loc_id}")
    async def delete_location_endpoint(loc_id: str):
        deleted = storage.delete_location(loc_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Location '{loc_id}' not found.")
        return {"deleted": loc_id}

    # --- Users CRUD & Per-User Toggle ---
    @app.get("/api/users")
    async def list_users_endpoint():
        return {"users": [u.model_dump() for u in storage.list_users()]}

    @app.post("/api/users")
    async def save_user_endpoint(user: UserProfile):
        if not user.id.strip():
            user.id = f"usr_{uuid.uuid4().hex[:8]}"
        if not user.name.strip():
            raise HTTPException(status_code=400, detail="User name cannot be empty.")
        user.timezone = validate_iana_timezone(user.timezone)
        for target in user.ha_notify_targets:
            if not is_allowed_notify_action(target):
                raise HTTPException(
                    status_code=400,
                    detail=f"Notify action '{target}' is not permitted by the allowlist.",
                )
        saved = storage.save_user(user)
        return saved.model_dump()

    @app.post("/api/users/{user_id}/toggle")
    async def toggle_user_endpoint(user_id: str, payload: TogglePayload):
        usr = storage.get_user(user_id)
        if not usr:
            raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")
        usr.enabled = payload.enabled
        saved = storage.save_user(usr)
        return saved.model_dump()

    @app.delete("/api/users/{user_id}")
    async def delete_user_endpoint(user_id: str):
        deleted = storage.delete_user(user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")
        return {"deleted": user_id}

    # --- Break Windows CRUD & Presets ---
    @app.get("/api/breaks")
    async def list_breaks_endpoint():
        return {"breaks": [b.model_dump() for b in storage.list_breaks()]}

    @app.post("/api/breaks")
    async def save_break_endpoint(brk: BreakWindow):
        if not brk.id.strip():
            brk.id = f"brk_{uuid.uuid4().hex[:8]}"
        if not brk.name.strip():
            raise HTTPException(status_code=400, detail="Break name cannot be empty.")
        if not storage.get_user(brk.user_id):
            raise HTTPException(status_code=400, detail=f"User '{brk.user_id}' does not exist.")
        saved = storage.save_break(brk)
        return saved.model_dump()

    @app.post("/api/breaks/preset")
    async def apply_break_preset(payload: PresetBreaksPayload):
        usr = storage.get_user(payload.user_id)
        if not usr:
            raise HTTPException(status_code=400, detail=f"User '{payload.user_id}' does not exist.")

        created: List[BreakWindow] = []
        work_loc_id = usr.fixed_location_id or "loc_work"

        if payload.preset == "workday_3_breaks":
            templates = [
                ("Morning Break Walk (10:00)", ActivityType.WALK, "10:00", 15, 30, 30, LocationRequirementMode.ONLY_AT_LOCATION, work_loc_id),
                ("Lunch Walk / Bike Ride (12:30)", ActivityType.WALK, "12:30", 30, 30, 30, LocationRequirementMode.ONLY_AT_LOCATION, work_loc_id),
                ("Afternoon Break Walk (15:00)", ActivityType.WALK, "15:00", 15, 30, 30, LocationRequirementMode.ONLY_AT_LOCATION, work_loc_id),
            ]
        elif payload.preset == "commute_and_workday":
            templates = [
                ("Morning Bike Ride to Work (08:00)", ActivityType.BIKE_COMMUTE, "08:00", 30, 20, 20, LocationRequirementMode.ANY_LOCATION, None),
                ("Morning Break Walk (10:00)", ActivityType.WALK, "10:00", 15, 30, 30, LocationRequirementMode.ONLY_AT_LOCATION, work_loc_id),
                ("Lunch Walk / Bike Ride (12:30)", ActivityType.WALK, "12:30", 30, 30, 30, LocationRequirementMode.ONLY_AT_LOCATION, work_loc_id),
                ("Afternoon Break Walk (15:00)", ActivityType.WALK, "15:00", 15, 30, 30, LocationRequirementMode.ONLY_AT_LOCATION, work_loc_id),
                ("Evening Bike Ride Home (17:00)", ActivityType.BIKE_COMMUTE, "17:00", 30, 20, 20, LocationRequirementMode.ONLY_AT_LOCATION, work_loc_id),
            ]
        elif payload.preset == "commute_bike":
            templates = [
                ("Morning Bike Commute (08:15)", ActivityType.BIKE_COMMUTE, "08:15", 30, 30, 30, LocationRequirementMode.ANY_LOCATION, None),
                ("Evening Bike Commute (17:15)", ActivityType.BIKE_COMMUTE, "17:15", 30, 30, 30, LocationRequirementMode.ONLY_AT_LOCATION, work_loc_id),
            ]
        else:
            templates = [
                ("Lunch Walk (12:30)", ActivityType.WALK, "12:30", 30, 30, 30, LocationRequirementMode.ANY_LOCATION, None),
            ]

        for name, act, st, dur, fb, fa, req_mode, req_loc in templates:
            b = BreakWindow(
                id=f"brk_{usr.id}_{st.replace(':', '')}",
                user_id=usr.id,
                name=name,
                activity_type=act,
                start_time=st,
                duration_minutes=dur,
                flex_before_minutes=fb,
                flex_after_minutes=fa,
                lead_alert_minutes=25 if "Commute" not in name else 20,
                active_days=[0, 1, 2, 3, 4],
                location_req_mode=req_mode,
                required_location_id=req_loc,
                urgency_override=UrgencyLevel.AUTO,
                notify_when_dry=False,
                enabled=True,
            )
            storage.save_break(b)
            created.append(b)

        return {"created": [c.model_dump() for c in created]}

    @app.delete("/api/breaks/{break_id}")
    async def delete_break_endpoint(break_id: str):
        deleted = storage.delete_break(break_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Break window '{break_id}' not found.")
        return {"deleted": break_id}

    # --- Evaluation & Test Notification Endpoints ---
    @app.post("/api/evaluate/run")
    async def run_evaluate_endpoint(payload: EvaluateRunPayload):
        result = await run_monitoring_cycle(
            target_break_id=payload.break_id,
            target_user_id=payload.user_id,
            send_notifications=payload.send_notifications,
            ignore_dedup=payload.ignore_dedup,
            manual_trigger=True,
        )
        return result

    @app.post("/api/test-notification")
    async def send_test_notification(payload: TestNotifyPayload):
        usr = storage.get_user(payload.user_id)
        if not usr:
            raise HTTPException(status_code=404, detail=f"User '{payload.user_id}' not found.")
        cfg = storage.get_config()
        locs = storage.list_locations()
        resolved = resolve_user_target_locations(usr, locs, state_cache["persons"])
        _, lname, _, _, _ = resolved[0]

        urg = "urgent" if payload.urgency == "urgent" else "neutral"
        msg = (
            payload.custom_message
            or f"Test notification for {usr.name} at {lname}. RainBreak is ready to advise your dry walk & bike windows!"
        )
        records = await dispatcher.dispatch_for_user(
            user=usr,
            config=cfg,
            title=f"RainBreak Test ({urg.upper()})",
            message=msg,
            urgency=urg,
            location_name=lname,
            alert_type="manual_test",
        )
        submitted = sum(1 for r in records if r.status == "submitted")
        failed = sum(1 for r in records if r.status == "failed")
        skipped = sum(1 for r in records if r.status == "skipped")
        return {
            "summary": {
                "total": len(records),
                "submitted": submitted,
                "failed": failed,
                "skipped": skipped,
            },
            "records": [r.model_dump() for r in records],
        }

    @app.post("/api/demo/scenario")
    async def set_demo_scenario_endpoint(payload: ScenarioPayload):
        allowed = {"workday_break_rain", "imminent_shower", "all_clear", "heavy_storm"}
        if payload.scenario not in allowed:
            raise HTTPException(status_code=400, detail=f"Unknown scenario '{payload.scenario}'.")
        weather_service.set_demo_scenario(payload.scenario)
        forecasts, evaluations = await build_all_forecasts_and_evaluations(force_refresh=True)
        return {
            "scenario": payload.scenario,
            "forecasts": [f.model_dump() for f in forecasts],
            "break_evaluations": [e.model_dump() for e in evaluations],
        }

    @app.get("/api/history")
    async def get_history_endpoint(limit: int = 100):
        return {"records": [r.model_dump() for r in storage.list_alert_history(limit=limit)]}

    @app.delete("/api/history")
    async def clear_history_endpoint():
        count = storage.clear_alert_history()
        return {"cleared": count}

    return app


app = create_app()
