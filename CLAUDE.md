# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

This is a **Home Assistant add-on repository** (`repository.yaml` marks the root). Each top-level folder is a self-contained add-on that Home Assistant builds and runs as a Docker container. There is no monorepo build tool, no CI, and no test suite — add-ons are built by the Home Assistant Supervisor from each folder's `config.yaml` + `Dockerfile`.

The three add-ons:

| Folder | Add-on | Stack | Notes |
|--------|--------|-------|-------|
| `ha_full_mcp/` | HA Full MCP Server | Python MCP server | The actively-developed one. Modular `src/api/` + `src/tools/` packages. |
| `ha_addons/` | HA Addon MCP Server | Python MCP server | Older/simpler predecessor of `ha_full_mcp`; flat `src/`, addon-only tools. |
| `baby_tracker/` | Baby Tracker | FastAPI + SQLite | Ingress web UI, unrelated to MCP. |

## Critical operational rules (from GEMINI.md)

These are enforced conventions, not suggestions — honor them before any commit/push:

1. **Version consistency.** When bumping an add-on version, update it in *all* places: `config.yaml` `version:`, the add-on's `README.md`/`CHANGELOG.md`, and any source constant (e.g. `ha_full_mcp/src/config.py` `ServerConfig.server_version`, `baby_tracker/app/main.py` `FastAPI(version=...)`). These drift easily — grep for the old version string to catch every occurrence.
2. **README sync.** The root `README.md` must list the current add-ons with correct names (matching `config.yaml`) and descriptions before pushing to GitHub.
3. **Support button.** Root and per-add-on `README.md` files carry the "Buy Me A Coffee" badge and Asgard footer.
4. Each add-on lives in its own root-level folder.

Commit convention (see `git log`): `type(addon_slug): vX.Y.Z — summary`, e.g. `fix(baby_tracker): v1.0.4 — five UX fixes`.

## Building / running

Add-ons run inside Home Assistant, so there is no local `npm`/`make` target. To iterate you either install the repo into a HA instance, or build the container manually:

```bash
# Build one add-on's image locally (uses the amd64 HA base image)
cd ha_full_mcp
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.19 -t ha_full_mcp .
```

- Base images per arch come from `build.json`; the MCP add-ons target **Alpine 3.19**, which is why `pip install` uses `--break-system-packages` (PEP 668).
- `run.sh` is the container entrypoint. In the MCP add-ons it uses `bashio::config` to read options; in `baby_tracker` it parses `/data/options.json` with inline `python3`.
- `baby_tracker` can also be run directly for UI work: `cd baby_tracker && pip install -r requirements.txt && uvicorn app.main:app --port 8765` (set `DATABASE_URL=sqlite:///./baby.db`).

There are **no tests** in this repo — do not fabricate a test command.

## MCP server architecture (`ha_full_mcp`, `ha_addons`)

Both MCP add-ons share the same shape; `ha_full_mcp` is the reference implementation.

**Config flow (this trips people up):**
`config.yaml` options → `run.sh` exports them as env vars via `bashio::config` → `src/config.py` `load_config()` reads env vars into a `ServerConfig`. Per-tool enable/disable flags travel as env vars named `SECTION_TOOLNAME` (e.g. option `addon_information.list_addons` → env `ADDON_INFORMATION_LIST_ADDONS`). `config.py` holds the authoritative `all_tools` map from tool-name → env-var-name and builds `enabled_tools`; **any new tool must be added in three places: `config.yaml` (options + schema), `config.py`'s `all_tools` map, and the tool's definitions module.**

**Transport.** `TRANSPORT=sse` (default) or `stdio`, dispatched in `src/server.py`. SSE mode builds a Starlette + uvicorn app; stdio uses `mcp.server.stdio`.

**Auth (`src/auth.py`).** API key checked via constant-time compare. Supported carriers: URL path param (`/sse/{api_key}`, `/messages/{api_key}` — preferred, survives Cloudflare proxying), query param, `Authorization: Bearer`, and `X-API-Key`. If no `api_key` option is set, one is generated at startup and printed to the log. CORS is intentionally `allow_origins=["*"]` because every endpoint is key-gated.

**Tool registration.** `src/mcp_handlers.py` aggregates tool definitions from each `tools/*` module and filters by `enabled_tools`. In `ha_full_mcp` the HA client is split into `src/api/*_api.py` (REST + WebSocket, re-exported through `src/ha_client.py`) and tool handlers into `src/tools/<domain>/`. Tool schema arrays must include `items` on array-typed params (a recurring bug fixed in v1.9.0).

## Baby Tracker architecture (`baby_tracker`)

Standard FastAPI layout under `app/`: `main.py` (routes + startup), `models.py` (SQLAlchemy), `schemas.py` (Pydantic), `crud.py`, `calculator.py` (age/growth math), `database.py`. Frontend is server-rendered static assets in `app/frontend/` + `app/static/` with client-side i18n (`static/js/i18n.js`, `nl`/`en`).

- DB is SQLite at `/data/db/baby_tracker.db` (HA-persistent `/data` volume).
- **Schema migrations** run on every startup in `main.py::_run_migrations()` — a list of idempotent `ALTER TABLE` statements wrapped in try/except. Add new columns there, not by editing existing `CREATE TABLE`s.
- Timezone handling has been a repeated source of bugs (see recent commits): timestamps are stored/emitted as full ISO with server-side offset. Preserve that when touching date logic.
