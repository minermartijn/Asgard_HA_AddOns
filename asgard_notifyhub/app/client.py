"""Home Assistant Core API client for service discovery and notification dispatch.

Strict Security Boundaries:
1. Only actions in the "notify" and "persistent_notification" domains are callable.
2. Arbitrary domain calls (e.g. system, light, shell_command) are strictly blocked.
3. In Demo or Standalone mode, a mock client provides realistic candidates without network calls.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Protocol
import httpx
from app.models import TargetService

logger = logging.getLogger("asgard_notifyhub.client")

ALLOWED_DOMAINS = {"notify", "persistent_notification"}


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

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def discover_services(self) -> list[TargetService]:
        """Discover available notification services from Home Assistant Core API."""
        self.last_error = None
        if not self.token:
            self.last_error = "Supervisor token not available. Ensure app has homeassistant_api enabled."
            logger.warning(self.last_error)
            return []

        url = f"{self.core_api_url}/services"
        data = None
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
                follow_redirects=False,
            ) as client:
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

        for item in data:
            if not isinstance(item, dict):
                continue
            domain = str(item.get("domain", "")).strip().lower()
            if domain not in ALLOWED_DOMAINS:
                continue

            domain_services = item.get("services", {})
            if isinstance(domain_services, dict):
                for s_name, s_info in domain_services.items():
                    name_str = str(s_name).strip()
                    info_dict = s_info if isinstance(s_info, dict) else {}
                    desc = info_dict.get("description")
                    friendly = info_dict.get("name") or f"{domain}.{name_str}"

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
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
                follow_redirects=False,
            ) as client:
                res_states = await client.get(f"{self.core_api_url}/states", headers=self._headers())
                if res_states.status_code == 200:
                    states_data = res_states.json()
                    if isinstance(states_data, list):
                        for entity in states_data:
                            if not isinstance(entity, dict):
                                continue
                            eid = str(entity.get("entity_id", "")).strip().lower()
                            if eid.startswith("notify."):
                                entity_svc_name = eid.split(".", 1)[1]
                                if not any(s.ha_domain == "notify" and s.ha_service == entity_svc_name for s in services):
                                    attrs = entity.get("attributes", {}) if isinstance(entity.get("attributes"), dict) else {}
                                    friendly = attrs.get("friendly_name") or eid
                                    services.append(
                                        TargetService(
                                            ha_domain="notify",
                                            ha_service=entity_svc_name,
                                            display_name=f"{friendly} ({eid})",
                                            description=f"Notification entity: {eid}",
                                            target_type="entity",
                                            supported=True,
                                        )
                                    )
        except Exception as exc:
            logger.debug("Optional notify entity discovery skipped: %s", exc)

        if not services and not self.last_error:
            self.last_error = "No compatible notification actions found in Home Assistant."

        # Sort: notify first, then alphabetically
        services.sort(key=lambda s: (0 if s.ha_domain == "notify" else 1, s.display_name.lower()))
        return services

    async def send_notification(
        self,
        domain: str,
        service: str,
        title: Optional[str],
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, Optional[str]]:
        """Call a notification service via Home Assistant Core API."""
        d_clean = domain.strip().lower()
        s_clean = service.strip().lower()

        # Strict Security Boundary
        if d_clean not in ALLOWED_DOMAINS:
            err = f"Security Violation: Domain '{domain}' is not an authorized notification domain."
            logger.error(err)
            return False, err

        if not self.token:
            err = "Authentication Error: No Supervisor token provided."
            logger.error(err)
            return False, err

        url = f"{self.core_api_url}/services/{d_clean}/{s_clean}"
        payload: dict[str, Any] = {"message": message}
        if title:
            payload["title"] = title
        if data and isinstance(data, dict):
            payload["data"] = data

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
                follow_redirects=False,
            ) as client:
                res = await client.post(url, headers=self._headers(), json=payload)
                if res.status_code in (200, 201):
                    return True, None
                err = f"Home Assistant rejected call with HTTP {res.status_code}: {res.text[:200]}"
                logger.warning(err)
                return False, err
        except httpx.TimeoutException:
            return False, "Request to Home Assistant Core API timed out."
        except Exception as exc:
            return False, f"Network error communicating with Home Assistant: {exc}"


class DemoHomeAssistantClient:
    """Mock client for development, standalone operation, and testing."""

    def __init__(self):
        self.dispatched_calls: list[dict[str, Any]] = []
        self.last_error: Optional[str] = None
        self.token = "demo_token"

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
                ha_service="mobile_app_partner_iphone",
                display_name="Partner's iPhone 15",
                description="Home Assistant Companion App for iOS",
                target_type="service",
                supported=True,
            ),
            TargetService(
                ha_domain="notify",
                ha_service="mobile_app_family_ipad",
                display_name="Living Room Family iPad",
                description="Wall-mounted tablet / iPad",
                target_type="service",
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
        if d_clean not in ALLOWED_DOMAINS:
            return False, f"Security Violation: Domain '{domain}' is not allowed."

        self.dispatched_calls.append(
            {
                "domain": d_clean,
                "service": service.strip().lower(),
                "title": title,
                "message": message,
                "data": data,
            }
        )
        return True, None
