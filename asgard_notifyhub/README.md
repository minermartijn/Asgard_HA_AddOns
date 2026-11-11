# ASGARD NotifyHub

> **Version: 0.1.4.** Centralized notification policy, quiet hours, recipient routing, and delivery auditing for Home Assistant.

ASGARD NotifyHub provides a centralized, privacy-respecting notification routing and policy management hub accessed directly through Home Assistant Ingress.

It acts as a smart dispatcher between your automations and your physical notify devices:

- **Recipient & Route Management:** Define household members, mapped to one or more Home Assistant notification services (e.g. mobile apps, persistent notifications, speakers).
- **Recipient Groups:** Group recipients into logical targets (e.g. `Admins`, `Family`, `Night Shift`).
- **Deterministic Quiet Hours Engine:** Timezone-aware, cross-midnight quiet windows (e.g. 22:00 to 07:00) with day-of-week masks and explicit urgent override policies.
- **Priority-Based Dispatch:** `informational`, `normal`, and `urgent` priority levels with minimum priority thresholds per route.
- **Dry-Run Simulator & Composer:** Test routing, quiet hours suppression, and deduplication before sending live notifications.
- **Strict Security Allowlist:** Enforces a rigid security boundary restricting invocations exclusively to the `notify` and `persistent_notification` domains—arbitrary command or service injection is impossible.
- **Delivery Honesty Invariant:** Clearly communicates "Submitted to Home Assistant action" rather than falsely asserting end-user physical device receipt.
- **Privacy-Safe Audit History:** In-process SQLite delivery logging (`/data/notifyhub.db`) with automatic 30-day retention and no plain-text message bodies in default logs.

---

## Architecture & Permissions

| Setting | Value | Why |
| --- | --- | --- |
| `ingress` | `true` | Accessible exclusively via Home Assistant Ingress. No external network ports are published. |
| `panel_admin` | `true` | Only administrators see NotifyHub in the sidebar. |
| `hassio_role` | `default` | Requests only basic Supervisor metadata permissions. |
| `homeassistant_api` | `true` | Required to query available notify services (`GET /core/api/services`) and trigger `notify.*` actions. |

---

## Installation

1. Add this repository to Home Assistant: **Settings → Apps → App store → ⋮ → Repositories** and enter:
   `https://github.com/minermartijn/Asgard_HA_AddOns`
2. Install **ASGARD NotifyHub** and click **Start**.
3. Open **NotifyHub** from the sidebar.

See [DOCS.md](DOCS.md) for full configuration, API usage, and quiet hours policy examples.

---

Built with ⚡ by Asgard.

### Support my caffeine addiction ☕
If this app helps bring peace and quiet to your smart home notifications, feel free to fuel my next coding session! My code is powered by high-quality caffeine—one cup equals approximately three features and only one new bug. 😉

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/minermartijn)
