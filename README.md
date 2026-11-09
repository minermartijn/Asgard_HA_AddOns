# Asgard Home Assistant Add-ons

[![Quality checks](https://github.com/minermartijn/Asgard_HA_AddOns/actions/workflows/ci.yml/badge.svg)](https://github.com/minermartijn/Asgard_HA_AddOns/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--ons-41BDF5)](https://www.home-assistant.io/)

**A collection of independently versioned Home Assistant add-ons**, with two MCP servers for AI-assisted home automation and add-on recovery, plus household utilities. Developed and maintained by [minermartijn](https://github.com/minermartijn).

## What is included?

| Add-on | Version | Purpose |
| --- | --- | --- |
| **[HA Full MCP Server](ha_full_mcp/README.md)** | 1.11.1 | MCP tools for device/entity queries, automations, integrations, diagnostics, configuration, backups and add-on administration. |
| **[HA Addon MCP Server — Lifeboat](ha_addons/README.md)** | 1.4.0 | Separate MCP recovery path for add-on logs, lifecycle actions, and targeted add-on backup/restore. |
| **[Home Stock](home_stock/README.md)** | 1.0.0 | Household stock quantities, a shopping list, and Home Assistant integration. |
| **[Baby Tracker](baby_tracker/)** | 1.0.5 | Mobile-friendly feeding, diaper, sleep and growth tracking. |

Versions above describe add-on manifests; they do not imply that corresponding GitHub Releases have already been published.

## Published MCP releases

- **[HA Full MCP Server v1.11.1](https://github.com/minermartijn/Asgard_HA_AddOns/releases/tag/ha-full-mcp-v1.11.1)** — 62 configured tools for broad Home Assistant management.
- **[HA Addon MCP Server (Lifeboat) v1.4.0](https://github.com/minermartijn/Asgard_HA_AddOns/releases/tag/ha-lifeboat-v1.4.0)** — 22 focused add-on maintenance and recovery tools.

Both are independently installable Home Assistant add-ons; publishing a GitHub Release does not automatically deploy the update to a running Home Assistant instance.

## Why two MCP servers?

An AI assistant that updates the MCP add-on it is connected to can lose its own communication channel during a failed update. The **Lifeboat** add-on runs separately, so it may still be available to inspect logs or restart/rebuild Full MCP if the Home Assistant host and Supervisor remain operational.

```mermaid
flowchart LR
    AI["MCP-compatible AI client"] -->|"Authenticated"| Full["Full MCP :8010"]
    AI -->|"Independent recovery"| Life["Lifeboat :8015"]
    Full --> Core["HA Core API"]
    Full --> Supervisor["HA Supervisor API"]
    Life --> Supervisor
    Supervisor -->|"Recover primary add-on"| Full
```

This is not a replacement for conventional backups: Lifeboat cannot fix a failed host, broken Supervisor, or lost network. Read the [architecture and limitations](docs/ARCHITECTURE.md).

## Installation

You need a Home Assistant installation that supports the **add-on store** (for example, Home Assistant OS or Supervised).

1. In Home Assistant, open the add-on store and choose the option to manage custom repositories.
2. Add this repository URL:

   ```text
   https://github.com/minermartijn/Asgard_HA_AddOns
   ```

3. Refresh the add-on store if necessary and install only the add-on(s) you need.
4. Follow the add-on's README and configure its required credentials before connecting a client.
5. Test in a non-critical environment before relying on administrative or recovery operations.

**Important:** The MCP endpoints can administer Home Assistant. Never expose their ports directly to the public internet. Prefer header-based API key authentication, TLS/VPN or an authenticated access gateway, and restrict dangerous tools where possible. Read [SECURITY.md](SECURITY.md) before configuring remote access.

## Documentation

- [Full MCP usage and tool reference](ha_full_mcp/README.md)
- [Lifeboat installation, limitations and recovery](ha_addons/README.md)
- [Architecture and trust boundaries](docs/ARCHITECTURE.md)
- [Compare all 62 Full MCP and 22 Lifeboat tools](docs/MCP_TOOLS.md)
- [Reproducible recovery demonstration plan](docs/DEMO.md) — no published demo recording yet
- [Contributing and running regression tests](CONTRIBUTING.md)
- [Development and maintainer guide](docs/MAINTAINING.md)
- [Release procedure](docs/RELEASING.md)
- [Current roadmap](docs/ROADMAP.md)
- [Vulnerability reporting](SECURITY.md)

## Development and releases

Each top-level add-on has its own `config.yaml`, `Dockerfile`, and version. Source code and regression tests live within the relevant add-on directory.

The proposed GitHub Actions workflow checks Python syntax, Home Assistant add-on metadata and existing MCP regression tests. Actual pass/fail results are shown in GitHub Actions; do not interpret an absent badge result as passing tests.

Release tags will be **namespaced per add-on** and must be published only after version checks and relevant Home Assistant testing.

## Help improve the project

Bug reports, documentation corrections, real-world testing feedback and focused pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md). For security issues, use the private reporting guidance in [SECURITY.md](SECURITY.md), not a public issue.

Developed as an independent hobby project; compatibility and feature claims are based on documented code, and broader external adoption is not yet established.

---

Built with ⚡ by Asgard.

### Support my caffeine addiction ☕

If these add-ons saved you time (or a headache), feel free to fuel my next coding session! My code is powered by high-quality caffeine—one cup equals approximately three features and only one new bug. 😉

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/minermartijn)
