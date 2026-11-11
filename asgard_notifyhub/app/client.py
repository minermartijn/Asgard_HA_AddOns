"""Home Assistant Core API client for service discovery and notification dispatch.

Strict Security Boundaries:
1. Only an explicit, action-level allowlist of notification actions is callable:
   - every legacy ``notify.<service>`` delivery action (except ``notify.send_message``,
     which is only used internally together with a ``notify.*`` entity), and
   - ``persistent_notification.create``.
   Actions that remove or change existing notifications (for example
   ``persistent_notification.dismiss`` / ``dismiss_all``) are never exposed or called.
2. Arbitrary domain calls (e.g. system, light, shell_command) are strictly blocked.
3. Every dispatch performs exactly one Home Assistant call. There are no automatic
   retries through alternative actions, so a single NotifyHub route can never produce
   duplicate notifications on a device.
4. In Demo or Standalone mode, a mock client provides realistic candidates without network calls.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, Protocol

import httpx

from app.models import TargetService

logger = logging.getLogger("asgard_notifyhub.client")

ALLOWED_DOMAINS = {"notify", "persistent_notification"}
# Explicit action-level allowlist for the persistent_notification domain.
ALLOWED_PERSISTENT_ACTIONS = {"create"}
# notify actions that are never valid as a stand-alone delivery destination.
BLOCKED_NOTIFY_ACTIONS = {"send_message"}

_SLUG_RE = re.compile(r"^[a-z0-9_]+$")


def is_allowed_action(domain: str, service: str) -> bool:
    """Return True if ``domain.service`` is an allowed notification *delivery* action."""
    d = (domain or "").strip().lower()
    s = (service or "").strip().lower()
    if not s or not _SLUG_RE.match(s):
        return False
    if d == "notify":
        return s not in BLOCKED_NOTIFY_ACTIONS
    if d == "persistent_notification":
        return s in ALLOWED_PERSISTENT_ACTIONS
    return False


def unsupported_action_reason(domain: str, service: str) -> str:
    d = (domain or "").strip().lower()
    s = (service or "").strip().lower()
    if d not in ALLOWED_DOMAINS:
        return f"Security: '{d}.{s}' is outside the notification allowlist and was not called."
    if d == "persistent_notification":
        return (
            f"Unsupported route: '{d}.{s}' is not a delivery action (only persistent_notification.create "
            "is allowed). Edit or delete this route."
        )
    if s in BLOCKED_NOTIFY_ACTIONS:
        return (
            "Unsupported route: notify.send_message needs a notify entity. Choose the specific "
            "notify entity or notify action for the device instead."
        )
    return f"Unsupported route: '{d}.{s}' is not a valid notification action name."


class HomeAssistantClient(Protocol):
    last_error: Optional[str]

    async def discover_services(self) -> list[TargetService]:
        ...

    async def send_notification(
        self,
        domain: str,
        service: str,
        title: Optional[str],
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, Optional[str]]:
        ...


def _summarize_ha_error(
    status_code: int,
    body: str,
    target: str,
    mode: str,
    entity_state: Optional[str],
    suggested_service: Optional[str] = None,
) -> str:
    """Build an actionable error message for a rejected Home Assistant call."""
    snippet = (body or "").strip()[:160]
    alt_hint = (
        f" Switch this route to '{suggested_service}' instead."
        if suggested_service
        else " Use the device's notify.mobile_app_* action instead."
    )
    if status_code == 400:
        if mode == "entity":
            return (
                f"Home Assistant rejected notify.send_message for {target} (HTTP 400). The entity "
                f"may not accept this payload.{alt_hint} " + (f"Details: {snippet}" if snippet else "")
            ).strip()
        return (
            f"Home Assistant rejected {target} (HTTP 400). The action may no longer exist or does not "
            "accept this payload. Click Sync Services and check the route. "
            + (f"Details: {snippet}" if snippet else "")
        ).strip()
    if status_code == 401:
        return "Home Assistant returned 401 Unauthorized. The Supervisor token is invalid."
    if status_code == 403:
        return "Home Assistant returned 403 Forbidden. Check the App's Home Assistant API permission."
    if status_code == 404:
        return f"Home Assistant could not find {target} (HTTP 404). Click Sync Services and update the route."
    if status_code >= 500:
        state_hint = f" Home Assistant reports the entity state as '{entity_state}'." if entity_state else ""
        if mode == "entity":
            return (
                f"The integration behind notification entity {target} raised an error while sending "
                f"(HTTP {status_code}).{state_hint} Home Assistant accepted the request, but the "
                "integration could not deliver it. This entity is likely incompatible with "
                f"notify.send_message for this device.{alt_hint}"
            )
        return (
            f"The integration behind {target} raised an error (HTTP {status_code}). Check the Home "
            "Assistant log for details."
        )
    return f"Home Assistant rejected call to {target} with HTTP {status_code}. {snippet}".strip()


class RestHomeAssistantClient:
    def __init__(
        self,
        core_api_url: str,
        token: Optional[str],
        timeout_seconds: float = 10.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.core_api_url = core_api_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.last_error: Optional[str] = None
        # Short names (without "notify.") of discovered notify entities and services.
        self._known_entities: set[str] = set()
        self._known_services: set[str] = set()
        self._entity_states: dict[str, str] = {}
        self._discovered_once = False

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
            follow_redirects=False,
        )

    async def discover_services(self) -> list[TargetService]:
        """Discover allowed notification actions and notify entities from Home Assistant Core API."""
        self.last_error = None
        if not self.token:
            self.last_error = "Supervisor token not available. Ensure app has homeassistant_api enabled."
            logger.warning(self.last_error)
            return []

        url = f"{self.core_api_url}/services"
        data = None
        try:
            async with self._client() as client:
                res = await client.get(url, headers=self._headers())
                if res.status_code == 401:
                    self.last_error = "Home Assistant Core API returned 401 Unauthorized. Invalid Supervisor token."
                    logger.warning(self.last_error)
                    return []
                elif res.status_code == 403:
                    self.last_error = "Home Assistant Core API returned 403 Forbidden. Check app permissions."
                    logger.warning(self.last_error)
                    return []
                elif res.status_code != 200:
                    self.last_error = f"Home Assistant Core API returned HTTP {res.status_code}."
                    logger.warning(self.last_error)
                    return []
                data = res.json()
        except httpx.TimeoutException:
            self.last_error = f"Connection to Home Assistant Core API timed out ({self.timeout_seconds}s)."
            logger.error(self.last_error)
            return []
        except Exception as exc:
            self.last_error = f"Failed to query Home Assistant /services: {exc}"
            logger.error(self.last_error)
            return []

        services: list[TargetService] = []
        if not isinstance(data, list):
            self.last_error = "Unexpected response structure from Home Assistant /services."
            return []

        known_services: set[str] = set()
        for item in data:
            if not isinstance(item, dict):
                continue
            domain = str(item.get("domain", "")).strip().lower()
            if domain not in ALLOWED_DOMAINS:
                continue

            domain_services = item.get("services", {})
            if not isinstance(domain_services, dict):
                continue
            for s_name, s_info in domain_services.items():
                name_str = str(s_name).strip().lower()
                if not is_allowed_action(domain, name_str):
                    continue
                info_dict = s_info if isinstance(s_info, dict) else {}
                desc = info_dict.get("description")
                friendly = info_dict.get("name") or f"{domain}.{name_str}"
                if domain == "notify":
                    known_services.add(name_str)
                services.append(
                    TargetService(
                        ha_domain=domain,
                        ha_service=name_str,
                        display_name=str(friendly),
                        description=str(desc) if desc else None,
                        target_type="service",
                        supported=True,
                    )
                )

        # Also discover modern notify.* entities via /states if available
        known_entities: set[str] = set()
        entity_states: dict[str, str] = {}
        try:
            async with self._client() as client:
                res_states = await client.get(f"{self.core_api_url}/states", headers=self._headers())
                if res_states.status_code == 200:
                    states_data = res_states.json()
                    if isinstance(states_data, list):
                        for entity in states_data:
                            if not isinstance(entity, dict):
                                continue
                            eid = str(entity.get("entity_id", "")).strip().lower()
                            if not eid.startswith("notify."):
                                continue
                            short = eid.split(".", 1)[1]
                            if not _SLUG_RE.match(short):
                                continue
                            known_entities.add(short)
                            state_val = entity.get("state")
                            if state_val is not None:
                                entity_states[short] = str(state_val)
                            if short in known_services:
                                # Same name exists as a legacy action; the action takes precedence.
                                continue
                            attrs = entity.get("attributes", {}) if isinstance(entity.get("attributes"), dict) else {}
                            friendly = attrs.get("friendly_name") or eid
                            alt = f"notify.mobile_app_{short}" if f"mobile_app_{short}" in known_services else None
                            services.append(
                                TargetService(
                                    ha_domain="notify",
                                    ha_service=short,
                                    display_name=str(friendly),
                                    description=f"Notification entity: {eid}",
                                    target_type="entity",
                                    supported=True,
                                    ha_state=str(state_val) if state_val is not None else None,
                                    preferred_alternative=alt,
                                )
                            )
        except Exception as exc:
            logger.debug("Optional notify entity discovery skipped: %s", exc)

        self._known_services = known_services
        self._known_entities = known_entities
        self._entity_states = entity_states
        self._discovered_once = True

        if not services and not self.last_error:
            self.last_error = "No compatible notification actions found in Home Assistant."

        # Sort: notify first, then alphabetically
        services.sort(key=lambda s: (0 if s.ha_domain == "notify" else 1, s.display_name.lower()))
        return services

    def resolve_mode(self, domain: str, service: str) -> str:
        """Return 'entity' if the target is a notify entity, otherwise 'service'."""
        d = domain.strip().lower()
        s = service.strip().lower()
        if s.startswith("notify."):
            s = s.split(".", 1)[1]
        if d == "notify" and s in self._known_entities and s not in self._known_services:
            return "entity"
        return "service"

    async def send_notification(
        self,
        domain: str,
        service: str,
        title: Optional[str],
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, Optional[str]]:
        """Submit one notification to Home Assistant (exactly one HTTP call, no fallbacks)."""
        d_clean = domain.strip().lower()
        s_clean = service.strip().lower()
        if d_clean == "notify" and s_clean.startswith("notify."):
            s_clean = s_clean.split(".", 1)[1]

        # Strict Security Boundary
        if d_clean not in ALLOWED_DOMAINS:
            err = f"Security Violation: Domain '{domain}' is not an authorized notification domain."
            logger.error(err)
            return False, err
        if not is_allowed_action(d_clean, s_clean):
            err = unsupported_action_reason(d_clean, s_clean)
            logger.warning("Blocked dispatch to unsupported action %s.%s", d_clean, s_clean)
            return False, err

        if not self.token:
            err = "Authentication Error: No Supervisor token provided."
            logger.error(err)
            return False, err

        # Ensure the entity/service classification is available (e.g. right after a restart).
        if d_clean == "notify" and not self._discovered_once:
            try:
                await self.discover_services()
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Discovery before dispatch failed: %s", exc)

        mode = self.resolve_mode(d_clean, s_clean)
        if mode == "entity":
            target = f"notify.{s_clean}"
            url = f"{self.core_api_url}/services/notify/send_message"
            # notify.send_message only accepts entity_id, message and title.
            payload: dict[str, Any] = {"entity_id": target, "message": message}
            if title:
                payload["title"] = title
        else:
            target = f"{d_clean}.{s_clean}"
            url = f"{self.core_api_url}/services/{d_clean}/{s_clean}"
            payload = {"message": message}
            if title:
                payload["title"] = title
            if d_clean == "notify" and data and isinstance(data, dict):
                payload["data"] = data

        try:
            async with self._client() as client:
                res = await client.post(url, headers=self._headers(), json=payload)
        except httpx.TimeoutException:
            # The request may still be processed by HA; never resend automatically.
            return False, (
                "Request to Home Assistant timed out. The notification may or may not have been "
                "submitted; it was not resent automatically to avoid duplicates."
            )
        except Exception as exc:
            return False, f"Network error communicating with Home Assistant: {exc}"

        if res.status_code in (200, 201):
            return True, None

        suggested = f"notify.mobile_app_{s_clean}" if f"mobile_app_{s_clean}" in self._known_services else None
        err = _summarize_ha_error(
            res.status_code,
            res.text,
            target,
            mode,
            self._entity_states.get(s_clean) if mode == "entity" else None,
            suggested_service=suggested if mode == "entity" else None,
        )
        # Never log message bodies; only the target and status code.
        logger.warning("Home Assistant rejected %s call to %s with HTTP %s", mode, target, res.status_code)
        return False, err


class DemoHomeAssistantClient:
    """Mock client for development, standalone operation, and testing."""

    def __init__(self):
        self.dispatched_calls: list[dict[str, Any]] = []
        self.last_error: Optional[str] = None
        self.token = "demo_token"
        # Optional map of "domain.service" -> error message to simulate HA failures in tests.
        self.fail_actions: dict[str, str] = {}

    async def discover_services(self) -> list[TargetService]:
        self.last_error = None
        return [
            TargetService(
                ha_domain="notify",
                ha_service="notify",
                display_name="Broadcast (notify.notify)",
                description="Default broadcast notification service",
                target_type="service",
                supported=True,
            ),
            TargetService(
                ha_domain="notify",
                ha_service="mobile_app_pixel",
                display_name="Martijn's Pixel 8 Pro",
                description="Home Assistant Companion App for Android",
                target_type="service",
                supported=True,
            ),
            TargetService(
                ha_domain="notify",
                ha_service="mobile_app_galaxy_watch5_with_an_exceptionally_long_service_identifier_name",
                display_name="Send a notification via mobile_app_galaxy_watch5_with_an_exceptionally_long_service_identifier_name",
                description=(
                    "This notification action is provided by a notification integration or notification group. "
                    "To change where notifications are sent or which options are available, update that integration or group."
                ),
                target_type="service",
                supported=True,
            ),
            TargetService(
                ha_domain="notify",
                ha_service="living_room_tv",
                display_name="Living Room TV",
                description="Notification entity: notify.living_room_tv",
                target_type="entity",
                supported=True,
            ),
            TargetService(
                ha_domain="persistent_notification",
                ha_service="create",
                display_name="Persistent Notification (HA Web UI)",
                description="Shows in Home Assistant notifications panel",
                target_type="service",
                supported=True,
            ),
        ]

    async def send_notification(
        self,
        domain: str,
        service: str,
        title: Optional[str],
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, Optional[str]]:
        d_clean = domain.strip().lower()
        s_clean = service.strip().lower()
        if d_clean not in ALLOWED_DOMAINS:
            return False, f"Security Violation: Domain '{domain}' is not allowed."
        if not is_allowed_action(d_clean, s_clean):
            return False, unsupported_action_reason(d_clean, s_clean)

        full = f"{d_clean}.{s_clean}"
        if full in self.fail_actions:
            return False, self.fail_actions[full]

        self.dispatched_calls.append(
            {
                "domain": d_clean,
                "service": s_clean,
                "title": title,
                "message": message,
                "data": data,
            }
        )
        return True, None
