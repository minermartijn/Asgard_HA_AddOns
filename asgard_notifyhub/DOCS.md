# ASGARD NotifyHub — Documentation

## Configuration Options

Configure options via the Home Assistant App Configuration tab:

```yaml
demo_mode: false
default_timezone: "UTC"
dedup_window_seconds: 300
retention_days: 30
```

- **`demo_mode`** (*boolean, default: `false`*): When enabled, uses simulated mock notify devices without making actual calls to Home Assistant Core.
- **`default_timezone`** (*string, default: `"UTC"`*): Fallback timezone used when recipients or policies do not specify a local timezone (e.g. `"Europe/Amsterdam"`, `"America/New_York"`).
- **`dedup_window_seconds`** (*integer, 10–3600, default: `300`*): Window in seconds to suppress identical messages sent to the same recipient.
- **`retention_days`** (*integer, 1–365, default: `30`*): Number of days before audit history logs are purged.

---

## Features

### 1. Quiet Hours Policy Engine

NotifyHub supports complex, deterministic quiet hours policies:
- **Cross-Midnight Windows:** Specify windows spanning midnight (such as `22:00` to `07:00`).
- **Day-of-Week Masks:** Restrict quiet hours to specific days (e.g. weekdays only).
- **Urgent Override:** If enabled, urgent messages bypass quiet hours and are immediately dispatched. If disabled, even urgent messages are silenced.

### 2. Priority Levels

1. **Informational:** Low priority messages. Silenced by quiet hours and filtered by routes requiring normal or urgent priority.
2. **Normal:** Standard notifications.
3. **Urgent:** Critical notifications (alarms, security alerts, water leaks). Bypasses quiet hours when policies permit.

### 3. REST API & Integration

ASGARD NotifyHub exposes an internal REST API for automations and scripts:

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
- **Quiet Hours Timezone:** Verify your timezone string is in valid IANA format (e.g. `Europe/Amsterdam`).
