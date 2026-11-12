# ASGARD NotifyHub — Documentation

## Configuration Options

Configure options via the Home Assistant App Configuration tab:

```yaml
demo_mode: false
default_timezone: "Europe/Amsterdam"
dedup_window_seconds: 300
retention_days: 30
```

- **`demo_mode`** (*boolean, default: `false`*): When enabled, uses simulated mock notify devices without making actual calls to Home Assistant Core.
- **`default_timezone`** (*string, default: `"Europe/Amsterdam"`*): Default IANA timezone used when creating new recipients or quiet hours policies (e.g. `"Europe/Amsterdam"`, `"UTC"`, `"America/New_York"`). Existing policies keep their explicitly configured timezone.
- **`dedup_window_seconds`** (*integer, 10–3600, default: `300`*): Window in seconds to suppress identical messages sent to the same recipient.
- **`retention_days`** (*integer, 1–365, default: `30`*): Number of days before audit history logs are purged.

---

## Features

### 1. Target Scope Selection (`Single Recipient | Group | Everyone`)

In the Message Composer, choose the target audience:
- **Single Recipient:** Sends only to the selected household member's active routes.
- **Group:** Sends to all members of the selected recipient group.
- **Everyone:** Broadcasts to all enabled household recipients and evaluates each recipient's active routes and policies.

### 2. Quiet Hours Policy Engine & Timezones

NotifyHub supports deterministic, timezone-aware quiet hours policies:
- **IANA Timezone Support:** Properly handles winter time (CET), summer time (CEST), and daylight-saving transitions (e.g. `Europe/Amsterdam`).
- **Cross-Midnight Windows:** Specify windows spanning midnight (such as `22:00` to `07:00`).
- **Day-of-Week Masks:** Restrict quiet hours to specific days (`0` = Monday through `6` = Sunday).
- **Urgent Override:** If enabled, urgent messages bypass quiet hours and are immediately submitted. If disabled, even urgent messages are silenced.
- **Orphaned Policy Detection:** If a recipient or group is deleted, any quiet hours policy referencing it is flagged as `Orphaned Target` so you can reassign it via **Edit** or delete it.

### 3. Priority Levels & Delivery Statuses

1. **Informational:** Low-priority messages. Filtered by routes requiring `normal` or `urgent` priority (`blocked_priority`) and silenced during quiet hours (`blocked_quiet_hours`).
2. **Normal:** Standard household notifications.
3. **Urgent:** Critical notifications (alarms, security alerts, water leaks). Bypasses quiet hours when the policy permits `urgent_override`.

Each route evaluation records one of the following statuses:
- `submitted` — Accepted by Home Assistant (physical device delivery is handled by the Home Assistant integration).
- `blocked_quiet_hours` — Silenced by an active quiet hours policy.
- `suppressed_duplicate` — Suppressed within the deduplication window.
- `blocked_priority` — Blocked because message priority is below the route's minimum priority.
- `route_disabled` — Skipped because the route is disabled.
- `recipient_disabled` — Skipped because the recipient is disabled.
- `invalid_route` — Blocked because the route targets an unsupported action.
- `failed` — Home Assistant rejected the action call.

### 4. Strict Action-Level Allowlist & Wear OS / Companion Devices

- Only valid notification delivery actions are exposed and callable: `notify.<service_or_entity>` (excluding standalone `notify.send_message`) and `persistent_notification.create`.
- Actions that delete notifications (`persistent_notification.dismiss`, `persistent_notification.dismiss_all`) are blocked at both discovery and dispatch time.
- **Wear OS / Galaxy Watch Note:** Some companion devices (such as Galaxy Watch5) expose both a `notify.<device>` entity and a `notify.mobile_app_<device>` service in Home Assistant, where the `notify.<device>` entity may return `HTTP 500` when invoked via `notify.send_message`. For Wear OS watches and mobile companion devices, prefer the `notify.mobile_app_<device>` action. NotifyHub never automatically retries a failed action through an alternative service, preventing duplicate notifications.

### 5. REST API & Integration

#### Dry-Run Simulator: `POST /api/send/preview`
```json
{
  "target_type": "recipient",
  "target_id": "rec_123",
  "priority": "normal",
  "title": "Laundry Done",
  "message": "The washing machine cycle has finished."
}
```

#### Notification Dispatch: `POST /api/send`
```json
{
  "target_type": "group",
  "target_id": "grp_parents",
  "priority": "urgent",
  "title": "Front Door Sensor",
  "message": "Front door opened while away."
}
```

---

## Troubleshooting

- **Discovered Actions Empty:** Ensure Home Assistant Core API is accessible and `homeassistant_api: true` is enabled. Click **Sync Services** in the top right of the dashboard.
- **Entity Route Returns HTTP 500:** Switch the route from `notify.<device>` to `notify.mobile_app_<device>` using the **Edit** button on the route card.
- **Quiet Hours Timezone:** Verify your timezone string is in valid IANA format (e.g. `Europe/Amsterdam`).
