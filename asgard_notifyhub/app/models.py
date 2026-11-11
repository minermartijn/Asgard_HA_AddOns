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
    FAILED = "failed"


class TargetType(str, Enum):
    RECIPIENT = "recipient"
    GROUP = "group"


class TargetService(BaseModel):
    ha_domain: str = "notify"
    ha_service: str
    display_name: str
    description: Optional[str] = None
    target_type: str = "service"  # "service" or "entity"
    supported: bool = True


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
    failures_24h: int = 0
    ha_connected: bool = False
    discovered_services_count: int = 0
    demo_mode: bool = False
