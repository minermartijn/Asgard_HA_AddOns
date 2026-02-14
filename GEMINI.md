# Asgard Home Assistant Addons - Workspace Context

## Workspace Purpose
This workspace is a dedicated Home Assistant Addon Repository containing multiple specialized addons. It is synced with the public GitHub repository: `https://github.com/minermartijn/Asgard_HA_AddOns`.

## Critical Operational Rules
1. **README Synchronization**: The root `README.md` file MUST always be updated before any push to GitHub. It must accurately reflect:
   - The current list of available addons.
   - Correct addon names (matching `config.yaml`).
   - Up-to-date descriptions and installation instructions.
2. **Version Consistency**: Addon versions must be consistent across `config.yaml`, internal `README.md`, and any source code constants (e.g., `src/config.py`).
3. **Multi-Addon Structure**: Each addon must live in its own dedicated folder within the root of this repository.

## Current Addons

### 1. HA Addon MCP Server (`ha_addons/`)
- **Name**: HA Addon MCP Server
- **Version**: 1.2.0
- **Purpose**: Bridge between Home Assistant and Model Context Protocol (MCP) clients.
- **Status**: Stable / Production Ready.

## Repository Information
- **URL**: `https://github.com/minermartijn/Asgard_HA_AddOns`
- **Maintainer**: minermartijn
