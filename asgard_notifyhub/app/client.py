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

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def discover_services(self) -> list[TargetService]:
        """Discover available notification services from Home Assistant Core API."""
        if not self.token:
            logger.warning("No Supervisor token configured; cannot discover services from Core API.")
            return []

        url = f"{self.core_api_url}/services"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
                follow_redirects=False,
            ) as client:
                res = await client.get(url, headers=self._headers())
                if res.status_code != 200:
                    logger.warning("Core API /services returned HTTP %s", res.status_code)
                    return []
                data = res.json()
        except Exception as exc:
            logger.error("Failed to query Home Assistant /services: %s", exc)
            return []

        services: list[TargetService] = []
        if not isinstance(data, list):
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

    async def discover_services(self) -> list[TargetService]:
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
                ha_service="mobile_app_martijn_phone",
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
