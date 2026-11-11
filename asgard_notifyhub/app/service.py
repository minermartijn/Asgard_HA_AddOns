"""Service coordinator managing storage, HA client, and routing engine."""

from __future__ import annotations

import logging
from typing import Optional
from app.models import (
    AppStatusSummary,
    QuietPolicy,
    Recipient,
    RecipientGroup,
    Route,
    TargetService,
    TargetType,
)
from app.storage import Storage
from app.client import HomeAssistantClient
from app.engine import RoutingEngine

logger = logging.getLogger("asgard_notifyhub.service")


class NotifyHubService:
    def __init__(
        self,
        storage: Storage,
        ha_client: HomeAssistantClient,
        demo_mode: bool = False,
    ):
        self.storage = storage
        self.ha_client = ha_client
        self.demo_mode = demo_mode
        self.engine = RoutingEngine(storage=storage, ha_client=ha_client)
        self._cached_services: Optional[list[TargetService]] = None
        self._ensure_seed_data()

    def _ensure_seed_data(self) -> None:
        recipients = self.storage.list_recipients()
        if not recipients:
            logger.info("Initializing NotifyHub with baseline default recipient and route.")
            # Default recipient
            admin = Recipient(
                id="rec_admin",
                name="Household Admin",
                timezone="UTC",
                enabled=True,
            )
            self.storage.save_recipient(admin)

            # Default route: Persistent Notification (safe, always works in HA)
            default_route = Route(
                id="rt_admin_persist",
                recipient_id="rec_admin",
                name="Home Assistant Notification Panel",
                ha_domain="persistent_notification",
                ha_service="create",
                enabled=True,
            )
            self.storage.save_route(default_route)

            # Default quiet hours policy
            default_policy = QuietPolicy(
                id="pol_admin_night",
                target_id="rec_admin",
                target_type=TargetType.RECIPIENT,
                quiet_start="22:00",
                quiet_end="07:00",
                day_mask=[0, 1, 2, 3, 4, 5, 6],
                timezone="UTC",
                urgent_override=True,  # Allow urgent alerts at night
                enabled=True,
            )
            self.storage.save_policy(default_policy)

            # Default group
            all_group = RecipientGroup(
                id="grp_all",
                name="All Household",
                description="Broadcast to all configured household members",
                recipient_ids=["rec_admin"],
            )
            self.storage.save_group(all_group)

    async def get_services(self, force_refresh: bool = False) -> list[TargetService]:
        if self._cached_services is None or force_refresh:
            self._cached_services = await self.ha_client.discover_services()
        return self._cached_services

    async def get_summary(self) -> AppStatusSummary:
        stats = self.storage.get_stats_24h()
        services = await self.get_services()
        ha_connected = len(services) > 0 or self.demo_mode

        return AppStatusSummary(
            recipients_count=stats["recipients_count"],
            routes_count=stats["routes_count"],
            groups_count=stats["groups_count"],
            policies_count=stats["policies_count"],
            submissions_24h=stats["submissions_24h"],
            blocked_quiet_hours_24h=stats["blocked_quiet_hours_24h"],
            failures_24h=stats["failures_24h"],
            ha_connected=ha_connected,
            discovered_services_count=len(services),
            demo_mode=self.demo_mode,
        )
