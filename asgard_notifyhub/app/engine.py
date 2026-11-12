"""Routing and Policy Engine for ASGARD NotifyHub.

Evaluates recipient targets, cross-midnight quiet hours, priority routing,
and deduplication with strict honesty ("submitted to HA", not "delivered").
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, time, timezone
from typing import Optional, Union
from zoneinfo import ZoneInfo

from app.models import (
    DeliveryRecord,
    DeliveryStatus,
    PreviewItem,
    PreviewResponse,
    Priority,
    QuietPolicy,
    Recipient,
    Route,
    SendRequest,
    TargetType,
)
from app.storage import Storage
from app.client import HomeAssistantClient, is_allowed_action, unsupported_action_reason

logger = logging.getLogger("asgard_notifyhub.engine")


def compute_content_hash(target_id: str, title: Optional[str], message: str) -> str:
    raw = f"{target_id}:{title or ''}:{message}".strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def evaluate_quiet_hours(
    policy: QuietPolicy,
    priority_or_dt: Union[Priority, datetime, None] = Priority.NORMAL,
    now_utc: Optional[datetime] = None,
    priority: Optional[Priority] = None,
) -> tuple[bool, str]:
    """Evaluate whether quiet hours are currently in effect for a policy.

    Returns:
        (is_quiet, reason_text)
    """
    if not policy.enabled:
        return False, "Policy is disabled"

    if isinstance(priority_or_dt, datetime):
        dt_utc = priority_or_dt
        eval_priority = priority or Priority.NORMAL
    else:
        eval_priority = priority or (priority_or_dt if isinstance(priority_or_dt, Priority) else Priority.NORMAL)
        dt_utc = now_utc or datetime.now(timezone.utc)

    # Urgent override check
    if eval_priority == Priority.URGENT and policy.urgent_override:
        return False, "Urgent priority overrides quiet hours"
    try:
        tz = ZoneInfo(policy.timezone)
        local_dt = dt_utc.astimezone(tz)
    except Exception:
        logger.warning("Policy %s has unknown timezone %r; evaluating in UTC", policy.id, policy.timezone)
        local_dt = dt_utc.astimezone(timezone.utc)

    # Parse HH:MM
    try:
        s_parts = [int(p) for p in policy.quiet_start.split(":")]
        e_parts = [int(p) for p in policy.quiet_end.split(":")]
        start_t = time(s_parts[0], s_parts[1])
        end_t = time(e_parts[0], e_parts[1])
    except Exception:
        return False, "Invalid quiet hours time format in policy"

    current_t = local_dt.time()
    current_weekday = local_dt.weekday()  # 0=Monday, 6=Sunday

    in_window = False
    if start_t <= end_t:
        # Same-day window (e.g. 13:00 to 15:00)
        if start_t <= current_t < end_t and current_weekday in policy.day_mask:
            in_window = True
    else:
        # Cross-midnight window (e.g. 22:00 to 07:00)
        # Evening part: current_t >= start_t on day_mask
        if current_t >= start_t and current_weekday in policy.day_mask:
            in_window = True
        # Morning part: current_t < end_t. Checked against yesterday's weekday
        elif current_t < end_t:
            yesterday_weekday = (current_weekday - 1) % 7
            if yesterday_weekday in policy.day_mask:
                in_window = True

    if in_window:
        return True, f"Silenced by quiet hours ({policy.quiet_start}–{policy.quiet_end} in {policy.timezone})"

    return False, "Outside quiet hours"


class RoutingEngine:
    def __init__(self, storage: Storage, ha_client: HomeAssistantClient):
        self.storage = storage
        self.ha_client = ha_client

    def resolve_recipients(self, request: SendRequest) -> list[Recipient]:
        rid = request.recipient_id or (request.target_id if request.target_type == "recipient" else None)
        if rid:
            r = self.storage.get_recipient(rid)
            return [r] if r else []

        gid = request.group_id or (request.target_id if request.target_type == "group" else None)
        if gid:
            g = self.storage.get_group(gid)
            if not g:
                return []
            recipients = []
            for r_id in g.recipient_ids:
                rec = self.storage.get_recipient(r_id)
                if rec:
                    recipients.append(rec)
            return recipients

        # Neither specified or target_type == "all": fallback to all enabled recipients
        return [r for r in self.storage.list_recipients() if r.enabled]

    def get_applicable_policies(self, recipient: Recipient, group_id: Optional[str] = None) -> list[QuietPolicy]:
        """Collect all policies affecting this recipient (direct or via group)."""
        all_policies = self.storage.list_policies()
        applicable: list[QuietPolicy] = []

        for pol in all_policies:
            if not pol.enabled:
                continue
            if pol.target_type == TargetType.GLOBAL:
                # Household-wide policy applies to every recipient.
                applicable.append(pol)
            elif pol.target_type == TargetType.RECIPIENT and pol.target_id == recipient.id:
                applicable.append(pol)
            elif pol.target_type == TargetType.GROUP:
                if group_id and pol.target_id == group_id:
                    applicable.append(pol)
                else:
                    # Check if recipient is a member of this group
                    grp = self.storage.get_group(pol.target_id)
                    if grp and recipient.id in grp.recipient_ids:
                        applicable.append(pol)

        return applicable

    def preview(
        self,
        request: SendRequest,
        now_utc: Optional[datetime] = None,
        dedup_window_seconds: int = 300,
    ) -> PreviewResponse:
        """Simulate notification routing and policy enforcement without sending."""
        dt = now_utc or datetime.now(timezone.utc)
        recipients = self.resolve_recipients(request)

        items: list[PreviewItem] = []
        would_submit = 0
        blocked = 0
        suppressed = 0

        for r in recipients:
            if not r.enabled:
                items.append(
                    PreviewItem(
                        recipient_id=r.id,
                        recipient_name=r.name,
                        route_id="none",
                        route_name="none",
                        ha_service="none",
                        status=DeliveryStatus.RECIPIENT_DISABLED,
                        reason="Recipient is disabled in NotifyHub",
                    )
                )
                blocked += 1
                continue

            # Check quiet hours policies
            policies = self.get_applicable_policies(r, request.group_id)
            is_silenced = False
            silence_reason = ""
            for pol in policies:
                quiet, reason = evaluate_quiet_hours(pol, request.priority, now_utc=dt)
                if quiet:
                    is_silenced = True
                    silence_reason = reason
                    break

            # Evaluate each route
            for route in r.routes:
                if not route.enabled:
                    items.append(
                        PreviewItem(
                            recipient_id=r.id,
                            recipient_name=r.name,
                            route_id=route.id,
                            route_name=route.name,
                            ha_service=f"{route.ha_domain}.{route.ha_service}",
                            status=DeliveryStatus.ROUTE_DISABLED,
                            reason="Route is disabled in NotifyHub",
                        )
                    )
                    blocked += 1
                    continue

                # Strict action-level allowlist (protects against legacy/stored invalid routes)
                if not is_allowed_action(route.ha_domain, route.ha_service):
                    items.append(
                        PreviewItem(
                            recipient_id=r.id,
                            recipient_name=r.name,
                            route_id=route.id,
                            route_name=route.name,
                            ha_service=f"{route.ha_domain}.{route.ha_service}",
                            status=DeliveryStatus.INVALID_ROUTE,
                            reason=unsupported_action_reason(route.ha_domain, route.ha_service),
                        )
                    )
                    blocked += 1
                    continue

                # Priority check
                if request.priority.level < route.priority_min.level:
                    items.append(
                        PreviewItem(
                            recipient_id=r.id,
                            recipient_name=r.name,
                            route_id=route.id,
                            route_name=route.name,
                            ha_service=f"{route.ha_domain}.{route.ha_service}",
                            status=DeliveryStatus.BLOCKED_PRIORITY,
                            reason=f"Message priority '{request.priority.value}' is below route minimum '{route.priority_min.value}'",
                        )
                    )
                    blocked += 1
                    continue

                if is_silenced:
                    items.append(
                        PreviewItem(
                            recipient_id=r.id,
                            recipient_name=r.name,
                            route_id=route.id,
                            route_name=route.name,
                            ha_service=f"{route.ha_domain}.{route.ha_service}",
                            status=DeliveryStatus.BLOCKED_QUIET_HOURS,
                            reason=silence_reason,
                        )
                    )
                    blocked += 1
                    continue

                # Deduplication check
                content_hash = compute_content_hash(r.id, request.title, request.message)
                if self.storage.is_recent_duplicate(content_hash, dedup_window_seconds, now=dt):
                    items.append(
                        PreviewItem(
                            recipient_id=r.id,
                            recipient_name=r.name,
                            route_id=route.id,
                            route_name=route.name,
                            ha_service=f"{route.ha_domain}.{route.ha_service}",
                            status=DeliveryStatus.SUPPRESSED_DUPLICATE,
                            reason=f"Identical message sent within {dedup_window_seconds}s deduplication window",
                        )
                    )
                    suppressed += 1
                    continue

                items.append(
                    PreviewItem(
                        recipient_id=r.id,
                        recipient_name=r.name,
                        route_id=route.id,
                        route_name=route.name,
                        ha_service=f"{route.ha_domain}.{route.ha_service}",
                        status=DeliveryStatus.SUBMITTED,
                        reason="Route active; would submit to Home Assistant",
                    )
                )
                would_submit += 1

        return PreviewResponse(
            priority=request.priority,
            items=items,
            would_submit_count=would_submit,
            blocked_count=blocked,
            suppressed_count=suppressed,
        )

    async def execute(
        self,
        request: SendRequest,
        dedup_window_seconds: int = 300,
    ) -> list[DeliveryRecord]:
        """Dispatch notifications to Home Assistant and record audit records."""
        now = datetime.now(timezone.utc)
        preview_res = self.preview(request, now_utc=now, dedup_window_seconds=dedup_window_seconds)

        records: list[DeliveryRecord] = []

        for item in preview_res.items:
            rec_id = f"del_{uuid.uuid4().hex[:12]}"
            c_hash = compute_content_hash(item.recipient_id, request.title, request.message)

            if item.status == DeliveryStatus.SUBMITTED:
                # Find route to extract domain/service and target data
                r = self.storage.get_recipient(item.recipient_id)
                route = next((rt for rt in (r.routes if r else []) if rt.id == item.route_id), None)
                ha_domain = route.ha_domain if route else "notify"
                ha_service = route.ha_service if route else item.ha_service.replace("notify.", "")
                t_data = route.target_data if route else {}
                if request.data:
                    merged_data = dict(t_data or {})
                    merged_data.update(request.data)
                else:
                    merged_data = t_data

                success, err_msg = await self.ha_client.send_notification(
                    domain=ha_domain,
                    service=ha_service,
                    title=request.title,
                    message=request.message,
                    data=merged_data,
                )

                if success:
                    record = DeliveryRecord(
                        id=rec_id,
                        idempotency_key=request.idempotency_key,
                        created_utc=now,
                        priority=request.priority,
                        title=request.title,
                        recipient_id=item.recipient_id,
                        recipient_name=item.recipient_name,
                        route_id=item.route_id,
                        route_name=item.route_name,
                        ha_service=item.ha_service,
                        status=DeliveryStatus.SUBMITTED,
                        details="Successfully submitted to Home Assistant action",
                        content_hash=c_hash,
                    )
                else:
                    record = DeliveryRecord(
                        id=rec_id,
                        idempotency_key=request.idempotency_key,
                        created_utc=now,
                        priority=request.priority,
                        title=request.title,
                        recipient_id=item.recipient_id,
                        recipient_name=item.recipient_name,
                        route_id=item.route_id,
                        route_name=item.route_name,
                        ha_service=item.ha_service,
                        status=DeliveryStatus.FAILED,
                        details=err_msg or "Home Assistant action invocation failed",
                        content_hash=c_hash,
                    )
            else:
                record = DeliveryRecord(
                    id=rec_id,
                    idempotency_key=request.idempotency_key,
                    created_utc=now,
                    priority=request.priority,
                    title=request.title,
                    recipient_id=item.recipient_id,
                    recipient_name=item.recipient_name,
                    route_id=item.route_id,
                    route_name=item.route_name,
                    ha_service=item.ha_service,
                    status=item.status,
                    details=item.reason,
                    content_hash=c_hash,
                )

            self.storage.record_delivery(record)
            records.append(record)

        return records
