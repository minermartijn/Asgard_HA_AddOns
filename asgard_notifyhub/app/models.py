"""Normalized data transfer objects for ASGARD NotifyHub.

All models adhere to strict privacy rules: raw push tokens and private message
bodies are never stored in plain text in default audit logs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class Priority(str, Enum):
    INFORMATIONAL = "informational"
    NORMAL = "normal"
    URGENT = "urgent"

    @property
    def level(self) -> int:
        levels = {
            Priority.INFORMATIONAL: 1,
            Priority.NORMAL: 2,
            Priority.URGENT: 3,
        }
        return levels.get(self, 2)

    def __lt__(self, other: Priority) -> bool:
        if not isinstance(other, Priority):
            return NotImplemented
        return self.level < other.level

    def __le__(self, other: Priority) -> bool:
        if not isinstance(other, Priority):
            return NotImplemented
        return self.level <= other.level

    def __gt__(self, other: Priority) -> bool:
        if not isinstance(other, Priority):
            return NotImplemented
        return self.level > other.level

    def __ge__(self, other: Priority) -> bool:
        if not isinstance(other, Priority):
            return NotImplemented
        return self.level >= other.level


class DeliveryStatus(str, Enum):
    SUBMITTED = "submitted"
    BLOCKED_QUIET_HOURS = "blocked_quiet_hours"
    SUPPRESSED_DUPLICATE = "suppressed_duplicate"
    ROUTE_DISABLED = "route_disabled"
    RECIPIENT_DISABLED = "recipient_disabled"
    BLOCKED_PRIORITY = "blocked_priority"
    INVALID_ROUTE = "invalid_route"
    FAILED = "failed"


# Statuses that mean NotifyHub intentionally did not call Home Assistant.
SUPPRESSED_STATUSES = {
    DeliveryStatus.BLOCKED_QUIET_HOURS,
    DeliveryStatus.SUPPRESSED_DUPLICATE,
    DeliveryStatus.BLOCKED_PRIORITY,
    DeliveryStatus.ROUTE_DISABLED,
    DeliveryStatus.RECIPIENT_DISABLED,
}
# Statuses that represent an error that needs the user's attention.
ERROR_STATUSES = {DeliveryStatus.FAILED, DeliveryStatus.INVALID_ROUTE}


class TargetType(str, Enum):
    RECIPIENT = "recipient"
    GROUP = "group"
    GLOBAL = "global"


class TargetService(BaseModel):
    ha_domain: str = "notify"
    ha_service: str
    display_name: str
    description: Optional[str] = None
    target_type: str = "service"  # "service" or "entity"
    supported: bool = True
    full_name: Optional[str] = None
    ha_state: Optional[str] = None  # state reported by Home Assistant for notify entities
    preferred_alternative: Optional[str] = None  # e.g. notify.mobile_app_<slug> when entity is paired with a mobile_app service

    def model_post_init(self, __context: Any) -> None:
        if not self.full_name:
            self.full_name = f"{self.ha_domain}.{self.ha_service}"


class Route(BaseModel):
    id: str
    recipient_id: str
    name: str
    ha_domain: str = "notify"
    ha_service: str
    target_data: Optional[dict[str, Any]] = None
    priority_min: Priority = Priority.INFORMATIONAL
    enabled: bool = True

    @property
    def full_action(self) -> str:
        return f"{self.ha_domain}.{self.ha_service}"


class Recipient(BaseModel):
    id: str
    name: str
    timezone: str = "UTC"
    enabled: bool = True
    routes: list[Route] = Field(default_factory=list)


class RecipientGroup(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    recipient_ids: list[str] = Field(default_factory=list)


class QuietPolicy(BaseModel):
    id: str
    target_id: str  # recipient_id or group_id
    target_type: TargetType = TargetType.RECIPIENT
    quiet_start: str = "22:00"  # HH:MM format
    quiet_end: str = "07:00"    # HH:MM format (cross-midnight supported)
    day_mask: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])  # 0=Mon..6=Sun
    timezone: str = "UTC"
    urgent_override: bool = False
    enabled: bool = True


class SendRequest(BaseModel):
    idempotency_key: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    recipient_id: Optional[str] = None
    group_id: Optional[str] = None
    title: Optional[str] = None
    message: str
    priority: Priority = Priority.NORMAL
    data: Optional[dict[str, Any]] = None


class PreviewItem(BaseModel):
    recipient_id: str
    recipient_name: str
    route_id: str
    route_name: str
    ha_service: str
    status: DeliveryStatus
    reason: str

    @property
    def will_send(self) -> bool:
        return self.status == DeliveryStatus.SUBMITTED

    @property
    def quiet_hours_active(self) -> bool:
        return self.status == DeliveryStatus.BLOCKED_QUIET_HOURS

    @property
    def dedup_hit(self) -> bool:
        return self.status == DeliveryStatus.SUPPRESSED_DUPLICATE

    @property
    def service_target(self) -> str:
        return self.ha_service


class PreviewResponse(BaseModel):
    priority: Priority
    items: list[PreviewItem]
    would_submit_count: int
    blocked_count: int
    suppressed_count: int


class DeliveryRecord(BaseModel):
    id: str
    idempotency_key: Optional[str] = None
    created_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    priority: Priority
    title: Optional[str] = None
    recipient_id: Optional[str] = None
    recipient_name: Optional[str] = None
    route_id: Optional[str] = None
    route_name: Optional[str] = None
    ha_domain: Optional[str] = None
    ha_service: str = ""
    status: DeliveryStatus
    details: Optional[str] = None
    content_hash: Optional[str] = None


class AppSettings(BaseModel):
    retention_days: int = 30
    dedup_window_seconds: int = 300
    max_retries: int = 2
    default_timezone: str = "UTC"
    demo_mode: bool = False


class AppStatusSummary(BaseModel):
    recipients_count: int = 0
    routes_count: int = 0
    groups_count: int = 0
    policies_count: int = 0
    submissions_24h: int = 0
    blocked_quiet_hours_24h: int = 0
    quiet_silenced_24h: int = 0
    failures_24h: int = 0
    ha_connected: bool = False
    ha_error: Optional[str] = None
    discovered_services_count: int = 0
    services_discovered: int = 0
    demo_mode: bool = False


class DispatchSummary(BaseModel):
    """Aggregated outcome of a dispatch, derived only from the delivery records.

    ``outcome`` is one of:
      - ``submitted``: every route was submitted to Home Assistant.
      - ``partial``: some routes were submitted, others suppressed or failed.
      - ``suppressed``: nothing was submitted, but nothing failed (policy decisions only).
      - ``failed``: nothing was submitted and at least one route failed.
      - ``no_routes``: the target resolved to no routes at all.
    """

    outcome: str
    total: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    submitted: int = 0
    suppressed: int = 0
    failed: int = 0


def summarize_records(records: list[DeliveryRecord]) -> DispatchSummary:
    counts: dict[str, int] = {}
    for r in records:
        key = r.status.value if isinstance(r.status, DeliveryStatus) else str(r.status)
        counts[key] = counts.get(key, 0) + 1
    submitted = counts.get(DeliveryStatus.SUBMITTED.value, 0)
    failed = sum(counts.get(s.value, 0) for s in ERROR_STATUSES)
    suppressed = sum(counts.get(s.value, 0) for s in SUPPRESSED_STATUSES)
    total = len(records)
    if total == 0:
        outcome = "no_routes"
    elif submitted == total:
        outcome = "submitted"
    elif submitted > 0:
        outcome = "partial"
    elif failed > 0:
        outcome = "failed"
    else:
        outcome = "suppressed"
    return DispatchSummary(
        outcome=outcome,
        total=total,
        counts=counts,
        submitted=submitted,
        suppressed=suppressed,
        failed=failed,
    )
