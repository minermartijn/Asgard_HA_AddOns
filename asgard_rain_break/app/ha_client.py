"""Home Assistant Core API client for discovering persons, zones, and notify actions."""

import logging
from typing import Dict, List, Optional, Tuple
import httpx

from app.models import (
    DiscoveredNotifyAction,
    DiscoveredPerson,
    DiscoveredZone,
    LocationMode,
    SavedLocation,
    UserProfile,
)

logger = logging.getLogger("asgard_rain_break.ha_client")

EXCLUDED_ACTIONS = {
    "notify.send_message",
    "persistent_notification.dismiss",
    "persistent_notification.dismiss_all",
}


def is_allowed_notify_action(action: str) -> bool:
    if not action or "." not in action:
        return False
    norm = action.strip().lower()
    if norm in EXCLUDED_ACTIONS:
        return False
    domain, service = norm.split(".", 1)
    if not service:
        return False
    if domain == "notify":
        return True
    if domain == "persistent_notification" and service == "create":
        return True
    return False


class HomeAssistantClient:
    def __init__(
        self,
        base_url: str = "http://supervisor/core/api",
        token: Optional[str] = None,
        demo_mode: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.demo_mode = demo_mode
        self._entity_set: set = set()
        self._service_set: set = set()
        self.demo_sent_notifications: List[dict] = []

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def check_connection(self) -> Tuple[bool, str]:
        if self.demo_mode:
            return True, "Demo Mode (Simulated HA Core)"
        if not self.token:
            return False, "Missing SUPERVISOR_TOKEN"
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(f"{self.base_url}/", headers=self._headers())
                if resp.status_code == 200:
                    return True, "Connected to Home Assistant Core"
                return False, f"HA Core returned HTTP {resp.status_code}"
        except Exception as exc:
            return False, f"HA Core unreachable: {exc}"

    async def discover_all(
        self,
    ) -> Tuple[List[DiscoveredPerson], List[DiscoveredZone], List[DiscoveredNotifyAction]]:
        if self.demo_mode:
            persons = [
                DiscoveredPerson(
                    entity_id="person.martijn",
                    name="Martijn",
                    state="work",
                    latitude=52.0907,
                    longitude=5.1214,
                    gps_accuracy=12.0,
                    source="device_tracker.mart_s25",
                ),
                DiscoveredPerson(
                    entity_id="person.elize",
                    name="Elize",
                    state="home",
                    latitude=52.3676,
                    longitude=4.9041,
                    gps_accuracy=10.0,
                    source="device_tracker.elize_s25",
                ),
            ]
            zones = [
                DiscoveredZone(
                    entity_id="zone.home",
                    name="Home",
                    latitude=52.3676,
                    longitude=4.9041,
                    radius_m=100.0,
                    icon="mdi:home",
                ),
                DiscoveredZone(
                    entity_id="zone.work",
                    name="Work / Office",
                    latitude=52.0907,
                    longitude=5.1214,
                    radius_m=150.0,
                    icon="mdi:briefcase",
                ),
            ]
            actions = [
                DiscoveredNotifyAction(
                    action="notify.mobile_app_mart_s25",
                    name="Mart S25 (Mobile App)",
                    description="Send a push notification via Home Assistant Companion App on Mart S25",
                    target_type="service",
                ),
                DiscoveredNotifyAction(
                    action="notify.mobile_app_elize_s25",
                    name="Elize S25 (Mobile App)",
                    description="Send a push notification via Home Assistant Companion App on Elize S25",
                    target_type="service",
                ),
                DiscoveredNotifyAction(
                    action="notify.mobile_app_galaxy_watch5_fhyw",
                    name="Galaxy Watch5 (Mobile App)",
                    description="Send a push notification to Galaxy Watch5 companion service",
                    target_type="service",
                ),
                DiscoveredNotifyAction(
                    action="notify.persistent_notification",
                    name="HA Persistent Notification",
                    description="Create a persistent notification in the Home Assistant sidebar",
                    target_type="service",
                ),
            ]
            self._service_set = {a.action for a in actions}
            return persons, zones, actions

        persons: List[DiscoveredPerson] = []
        zones: List[DiscoveredZone] = []
        actions_map: Dict[str, DiscoveredNotifyAction] = {}
        self._entity_set.clear()
        self._service_set.clear()

        if not self.token:
            return persons, zones, []

        async with httpx.AsyncClient(timeout=8.0) as client:
            # 1. Fetch states for person.*, zone.*, and notify.* entities
            try:
                resp = await client.get(f"{self.base_url}/states", headers=self._headers())
                if resp.status_code == 200:
                    states = resp.json()
                    for st in states:
                        eid = str(st.get("entity_id") or "")
                        attrs = st.get("attributes") or {}
                        fname = str(attrs.get("friendly_name") or eid)
                        if eid.startswith("person."):
                            lat = attrs.get("latitude")
                            lon = attrs.get("longitude")
                            persons.append(
                                DiscoveredPerson(
                                    entity_id=eid,
                                    name=fname,
                                    state=str(st.get("state") or "unknown"),
                                    latitude=float(lat) if lat is not None else None,
                                    longitude=float(lon) if lon is not None else None,
                                    gps_accuracy=float(attrs["gps_accuracy"]) if attrs.get("gps_accuracy") is not None else None,
                                    source=attrs.get("source"),
                                )
                            )
                        elif eid.startswith("zone."):
                            lat = attrs.get("latitude")
                            lon = attrs.get("longitude")
                            if lat is not None and lon is not None:
                                zones.append(
                                    DiscoveredZone(
                                        entity_id=eid,
                                        name=fname,
                                        latitude=float(lat),
                                        longitude=float(lon),
                                        radius_m=float(attrs.get("radius") or 100.0),
                                        icon=str(attrs.get("icon") or "mdi:map-marker"),
                                    )
                                )
                        elif eid.startswith("notify.") and is_allowed_notify_action(eid):
                            self._entity_set.add(eid)
                            actions_map[eid] = DiscoveredNotifyAction(
                                action=eid,
                                name=fname,
                                description=f"Notification entity ({eid})",
                                target_type="entity",
                            )
            except Exception as exc:
                logger.warning("Failed to fetch HA states: %s", exc)

            # 2. Fetch services for notify.* and persistent_notification.create
            try:
                resp = await client.get(f"{self.base_url}/services", headers=self._headers())
                if resp.status_code == 200:
                    domains = resp.json()
                    for dom_obj in domains:
                        domain = dom_obj.get("domain")
                        if domain not in ("notify", "persistent_notification"):
                            continue
                        svcs = dom_obj.get("services") or {}
                        for s_name, s_meta in svcs.items():
                            full_action = f"{domain}.{s_name}"
                            if not is_allowed_notify_action(full_action):
                                continue
                            self._service_set.add(full_action)
                            title = str((s_meta or {}).get("name") or full_action)
                            desc = str((s_meta or {}).get("description") or "")
                            actions_map[full_action] = DiscoveredNotifyAction(
                                action=full_action,
                                name=title,
                                description=desc,
                                target_type="service",
                            )
            except Exception as exc:
                logger.warning("Failed to fetch HA services: %s", exc)

        # Mark companion mobile_app preferred alternatives
        for act_id, act_obj in actions_map.items():
            if act_obj.target_type == "entity" and act_id.startswith("notify."):
                slug = act_id.split(".", 1)[1]
                companion = f"notify.mobile_app_{slug}"
                if companion in actions_map:
                    act_obj.preferred_alternative = companion

        actions = sorted(actions_map.values(), key=lambda a: (0 if "mobile_app_" in a.action else 1, a.action))
        return persons, zones, actions

    async def send_ha_notification(
        self,
        action: str,
        title: str,
        message: str,
        urgency: str = "neutral",
    ) -> Tuple[bool, str]:
        if not is_allowed_notify_action(action):
            return False, f"Action '{action}' is not in the allowed notify action list."

        if self.demo_mode:
            self.demo_sent_notifications.append(
                {
                    "action": action,
                    "title": title,
                    "message": message,
                    "urgency": urgency,
                }
            )
            return True, f"Demo Mode: simulated HA call to {action} ({urgency})"

        if not self.token:
            return False, "Missing SUPERVISOR_TOKEN for Home Assistant API"

        domain, service = action.split(".", 1)
        is_entity = action in self._entity_set and action not in self._service_set

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                if is_entity:
                    url = f"{self.base_url}/services/notify/send_message"
                    payload = {
                        "entity_id": action,
                        "title": title,
                        "message": message,
                    }
                else:
                    url = f"{self.base_url}/services/{domain}/{service}"
                    payload = {
                        "title": title,
                        "message": message,
                    }
                    if domain == "notify" and urgency == "urgent":
                        payload["data"] = {
                            "ttl": 0,
                            "priority": "high",
                            "importance": "high",
                            "channel": "rain_urgent",
                            "push": {"interruption-level": "time-sensitive"},
                        }

                resp = await client.post(url, headers=self._headers(), json=payload)
                if 200 <= resp.status_code < 300:
                    return True, f"Submitted to Home Assistant via {action}"
                return False, f"Home Assistant returned HTTP {resp.status_code} for {action}: {resp.text[:160]}"
            except Exception as exc:
                return False, f"HA request error for {action}: {exc}"


def resolve_user_target_locations(
    user: UserProfile,
    saved_locations: List[SavedLocation],
    discovered_persons: List[DiscoveredPerson],
    override_location_id: Optional[str] = None,
) -> List[Tuple[str, str, float, float, str]]:
    """
    Resolve the active (location_id, location_name, lat, lon, source_type) tuples for a user.
    Supports:
    - override_location_id (e.g. per-break location override)
    - LocationMode.LIVE_PERSON (live GPS from HA person.* entity, with fallback to preset)
    - LocationMode.FIXED_LOCATION (single preset location)
    - LocationMode.MULTI_LOCATION (all selected watched_location_ids)
    """
    loc_by_id = {loc.id: loc for loc in saved_locations}
    default_loc = saved_locations[0] if saved_locations else SavedLocation(
        id="loc_default", name="Default (NL)", latitude=52.3676, longitude=4.9041
    )

    if override_location_id and override_location_id in loc_by_id:
        loc = loc_by_id[override_location_id]
        return [(loc.id, loc.name, loc.latitude, loc.longitude, "break_override")]

    if user.location_mode == LocationMode.LIVE_PERSON:
        person = next((p for p in discovered_persons if p.entity_id == user.ha_person_entity), None)
        if person and person.latitude is not None and person.longitude is not None:
            zone_hint = f" · {person.state}" if person.state and person.state not in ("unknown", "unavailable") else ""
            return [
                (
                    f"live_{user.id}",
                    f"{person.name} Live Location{zone_hint}",
                    person.latitude,
                    person.longitude,
                    f"live_person:{person.entity_id}",
                )
            ]
        # Fallback if person entity has no GPS coordinates right now
        fb_id = user.fallback_location_id or user.fixed_location_id
        fb = loc_by_id.get(fb_id or "", default_loc)
        return [(fb.id, f"{fb.name} (Fallback for {user.name})", fb.latitude, fb.longitude, "live_fallback")]

    if user.location_mode == LocationMode.FIXED_LOCATION:
        fixed = loc_by_id.get(user.fixed_location_id or "", default_loc)
        return [(fixed.id, fixed.name, fixed.latitude, fixed.longitude, "fixed_location")]

    # LocationMode.MULTI_LOCATION
    results: List[Tuple[str, str, float, float, str]] = []
    for lid in user.watched_location_ids:
        if lid in loc_by_id:
            loc = loc_by_id[lid]
            results.append((loc.id, loc.name, loc.latitude, loc.longitude, "multi_location"))
    if not results:
        results.append((default_loc.id, default_loc.name, default_loc.latitude, default_loc.longitude, "default"))
    return results
