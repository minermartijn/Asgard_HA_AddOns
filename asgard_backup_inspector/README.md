# ASGARD Backup Inspector

> **Version: 0.3.0.** Read-only dashboard for Home Assistant and Google Drive backup metadata. Read [Limitations](#limitations) before relying on it.

A read-only dashboard, opened from the Home Assistant sidebar, that answers critical backup questions: **is a recent backup listed, and is an off-site copy confirmed?**

It shows:

- **Backup Freshness & Redundancy Matrix:** Independent evaluations for Local Freshness, Cloud Freshness, Off-Site Coverage, and Full-Backup Coverage;
- **Multi-Location Backup Discovery:** Discovers and merges local Supervisor backups and cloud backups managed by the popular Home Assistant Google Drive Backup add-on;
- **Google Drive Status Overview:** Real-time sync status, cloud storage usage, available Google Drive free space, and last successful upload timestamp;
- **Deduplicated Inventory:** Accurately deduplicates archives present in both locations to display true unique counts and sizes without double-counting;
- **Location Filtering:** Filter table records by *All Locations*, *Both (Local + Drive)*, *Local Only*, *Google Drive Only*, or *Pending Upload*;
- **Storage Breakdown:** Total known backup storage, split by backup type and storage locations;
- **Chronological Timeline:** Visual timeline of recent backups showing age, location, and type relative to the freshness threshold;
- **Searchable Table:** Live keyword search, type/location/protection filters, sortable columns, and pagination;
- **Storage History Trend:** Safe, persistent local snapshot measurements under `/data/history.json`.

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
| `homeassistant_api` | `true` | Used exclusively to query the Google Drive Backup sensor state (`GET /core/api/states/sensor.backup_state`). No write or management endpoints are ever called. |

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
