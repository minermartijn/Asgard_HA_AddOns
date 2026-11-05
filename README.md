# Asgard Home Assistant Addons

This repository contains a collection of custom Home Assistant addons maintained by Asgard.

## Available Addons

### [HA Addon MCP Server (Lifeboat)](./ha_addons)
A lightweight Model Context Protocol (MCP) server dedicated to add-on lifecycle and emergency recovery (port 8015). Enables AI assistants to inspect logs, create and inspect single-add-on backups, restore a verified add-on backup, restart, rebuild, or fix add-ons even if the main Home Assistant MCP server goes offline during updates. Supports Streamable HTTP and SSE transports.

### [HA Full MCP Server](./ha_full_mcp)
A comprehensive Model Context Protocol (MCP) server that enables AI assistants to manage and control your entire Home Assistant installation (areas, devices, config entries, entities, automation discovery and management, backups, diagnostics), supporting both Streamable HTTP and SSE transports concurrently.

### [Home Stock](./home_stock)
A beautiful, low-friction household stock & shopping tracker. Tap to adjust quantities, get an automatic shopping list, push it straight to Home Assistant's own to-do list, and expose stock sensors for your dashboards and automations.

### [Baby Tracker](./baby_tracker)
Track your baby's feedings, diapers, weight and growth with a friendly, mobile-first interface (Dutch & English).

## How to use this repository

To add these addons to your Home Assistant instance:

1. Open your Home Assistant UI.
2. Navigate to **Settings > Add-ons**.
3. Click the **Add-on Store** button in the bottom right.
4. Click the three vertical dots (menu) in the top right corner.
5. Select **Repositories**.
6. Paste the following URL and click **Add**:
   `https://github.com/minermartijn/Asgard_HA_AddOns`
7. Once added, the addons will appear in the "Local Add-ons" or "Asgard Home Assistant Addons" section.

## Development

All addons are developed following the official Home Assistant Add-on standards but using generic base images to ensure compatibility across local development environments.

---
Built with ⚡ by Asgard.

### Support my caffeine addiction ☕
If these addons saved you some time (or a headache), feel free to fuel my next coding session! My code is powered by high-quality caffeine—one cup equals approximately three features and only one new bug. 😉

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/minermartijn)
