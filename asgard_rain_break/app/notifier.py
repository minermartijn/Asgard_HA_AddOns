"""Multi-channel notification dispatcher supporting Home Assistant Notify and Pushover API."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
import uuid
import httpx

from app.ha_client import HomeAssistantClient
from app.models import AlertLogRecord, AppConfig, UserProfile
from app.storage import Storage


class PushoverClient:
    PUSHOVER_URL = "https://api.pushover.net/1/messages.json"

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.demo_sent_messages: List[dict] = []

    async def send_message(
        self,
        app_token: str,
        user_key: str,
        title: str,
        message: str,
        urgency: str = "neutral",
        urgent_priority: int = 1,
        device: str = "",
        sound: str = "pushover",
    ) -> Tuple[bool, str]:
        token = (app_token or "").strip()
        user = (user_key or "").strip()
        if not token:
            return False, "Missing Pushover App API Token (configure per user or in Global Settings)."
        if not user:
            return False, "Missing Pushover User/Group API Key for this user."

        priority = urgent_priority if urgency == "urgent" else 0
        payload = {
            "token": token,
            "user": user,
            "title": title,
            "message": message,
            "priority": str(priority),
        }
        if device.strip():
            payload["device"] = device.strip()
        if sound.strip():
            payload["sound"] = sound.strip()
        if priority == 2:
            # Pushover Emergency Priority (2) requires retry and expire parameters
            payload["retry"] = "60"
            payload["expire"] = "1800"

        if self.demo_mode or token.startswith("demo_"):
            self.demo_sent_messages.append(payload)
            return True, f"Demo Mode: simulated Pushover dispatch (priority={priority}, user={user[:6]}…)"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.PUSHOVER_URL, data=payload)
                if resp.status_code == 200:
                    return True, f"Delivered to Pushover API (priority={priority})"
                return False, f"Pushover API HTTP {resp.status_code}: {resp.text[:160]}"
        except Exception as exc:
            return False, f"Pushover request error: {exc}"


class NotificationDispatcher:
    def __init__(
        self,
        storage: Storage,
        ha_client: HomeAssistantClient,
        pushover_client: PushoverClient,
    ):
        self.storage = storage
        self.ha_client = ha_client
        self.pushover_client = pushover_client

    async def dispatch_for_user(
        self,
        user: UserProfile,
        config: AppConfig,
        title: str,
        message: str,
        urgency: str,
        location_name: str,
        alert_type: str = "break_advice",
        break_id: Optional[str] = None,
        break_name: Optional[str] = None,
    ) -> List[AlertLogRecord]:
        records: List[AlertLogRecord] = []
        now_iso = datetime.now(timezone.utc).isoformat()
        formatted_title = f"🚨 [URGENT] {title}" if urgency == "urgent" and not title.startswith("🚨") else title

        # 1. Home Assistant Notify targets
        if user.ha_notify_enabled and user.ha_notify_targets:
            for target_action in user.ha_notify_targets:
                ok, detail = await self.ha_client.send_ha_notification(
                    action=target_action,
                    title=formatted_title,
                    message=message,
                    urgency=urgency,
                )
                rec = AlertLogRecord(
                    id=f"alt_{uuid.uuid4().hex[:10]}",
                    timestamp=now_iso,
                    user_id=user.id,
                    user_name=user.name,
                    break_id=break_id,
                    break_name=break_name,
                    location_name=location_name,
                    alert_type=alert_type,
                    urgency=urgency,
                    channel="ha_notify",
                    target=target_action,
                    status="submitted" if ok else "failed",
                    title=formatted_title,
                    message_preview=message[:220],
                    detail=detail,
                )
                self.storage.add_alert_log(rec)
                records.append(rec)

        # 2. Pushover channel
        if user.pushover_enabled:
            effective_token = (user.pushover_app_token or "").strip() or (config.pushover_app_token or "").strip()
            ok, detail = await self.pushover_client.send_message(
                app_token=effective_token,
                user_key=user.pushover_user_key,
                title=formatted_title,
                message=message,
                urgency=urgency,
                urgent_priority=user.pushover_urgent_priority,
                device=user.pushover_device,
                sound=user.pushover_sound,
            )
            masked_user = (
                f"pushover:{user.pushover_user_key[:5]}…"
                if len(user.pushover_user_key or "") >= 5
                else "pushover:unconfigured"
            )
            rec = AlertLogRecord(
                id=f"alt_{uuid.uuid4().hex[:10]}",
                timestamp=now_iso,
                user_id=user.id,
                user_name=user.name,
                break_id=break_id,
                break_name=break_name,
                location_name=location_name,
                alert_type=alert_type,
                urgency=urgency,
                channel="pushover",
                target=masked_user,
                status="submitted" if ok else "failed",
                title=formatted_title,
                message_preview=message[:220],
                detail=detail,
            )
            self.storage.add_alert_log(rec)
            records.append(rec)

        if not records:
            rec = AlertLogRecord(
                id=f"alt_{uuid.uuid4().hex[:10]}",
                timestamp=now_iso,
                user_id=user.id,
                user_name=user.name,
                break_id=break_id,
                break_name=break_name,
                location_name=location_name,
                alert_type=alert_type,
                urgency=urgency,
                channel="none",
                target="no_active_channels",
                status="skipped",
                title=formatted_title,
                message_preview=message[:220],
                detail="No notification channels (HA Notify or Pushover) are enabled/configured for this user.",
            )
            self.storage.add_alert_log(rec)
            records.append(rec)

        return records
