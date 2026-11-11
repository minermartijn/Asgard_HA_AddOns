# ASGARD Backup Inspector

> **Status: experimental (0.1.0, unreleased).** Not yet installation-tested on a real Home Assistant system. Read [Limitations](#limitations) before relying on it.

A read-only dashboard, opened from the Home Assistant sidebar, that answers one question: **is a recent backup listed?**

It shows:

- how many backups the Supervisor lists;
- the age of the most recent one, compared with a staleness threshold you choose (48 hours by default);
- the total size of backups whose size is known (backups without a size are counted separately, never as 0);
- a table with date, age, name, type, size, password protection and storage locations.

## What it does not do

The App cannot create, delete, restore, download or decrypt backups. It has no code path that calls those Supervisor endpoints. It does not change backup schedules and does not send data anywhere.

A green status means **a recent backup appears in the metadata**. It does **not** mean the backup can be restored. Test restores separately.

## Permissions

| Setting | Value | Why |
| --- | --- | --- |
| `ingress` | `true` | The UI is only reachable through Home Assistant's authenticated Ingress. No host port is published. |
| `panel_admin` | `true` | Only administrators see it in the sidebar. |
| `hassio_api` | `true` | Needed to call `GET /backups/info` on the Supervisor. |
| `hassio_role` | `default` | The Supervisor's `default` role allows read-only paths ending in `/info`. The broader `backup` role (create/restore/delete) is **not** requested. |
| `homeassistant_api` | not set | The App does not use the Home Assistant Core API. |

The web server also refuses connections that don't come from the Supervisor's Ingress proxy.

## Installation

1. Add this repository to Home Assistant: **Settings → Apps → App store → ⋮ → Repositories** and enter `https://github.com/minermartijn/Asgard_HA_AddOns`.
2. Install **ASGARD Backup Inspector** and start it.
3. Open **Backup Inspector** from the sidebar.

See [DOCS.md](DOCS.md) for options and troubleshooting.

## Limitations

- Experimental: so far, verification consists of automated tests against synthetic Supervisor responses and a local container smoke test. It has not yet been installed on a real Home Assistant system.
- Only `amd64` is listed until other architectures have been built and tested.
- The App only sees backups that the Supervisor lists. Backups stored outside the Supervisor's locations are not included.

---
Built with ⚡ by Asgard.

### Support my caffeine addiction ☕
If this app gave you peace of mind about your backups, feel free to fuel my next coding session! My code is powered by high-quality caffeine—one cup equals approximately three features and only one new bug. 😉

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/minermartijn)
