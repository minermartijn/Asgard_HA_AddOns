# Maintainer guide

This is the development and release reference for **Asgard Home Assistant Apps**. The apps are independently versioned and packaged as Home Assistant app containers. See [CONTRIBUTING.md](../CONTRIBUTING.md), [SECURITY.md](../SECURITY.md), and [release procedures](RELEASING.md).

## Apps and layout

| Folder | App | Technology | Main responsibility |
| --- | --- | --- | --- |
| `ha_full_mcp/` | HA Full MCP Server | Python / MCP / Home Assistant APIs | Broad Home Assistant management and diagnostics |
| `ha_addons/` | HA Addon MCP Server (Lifeboat) | Python / MCP / Supervisor API | Separate app administration and recovery |
| `baby_tracker/` | Baby Tracker | FastAPI / SQLite | Feeding, sleep, diaper and growth tracking |
| `home_stock/` | Home Stock | FastAPI / SQLite | Household inventory and shopping-list integration |
| `asgard_backup_inspector/` | ASGARD Backup Inspector | FastAPI / Ingress | Read-only backup metadata freshness and size dashboard |

The root `repository.yaml` declares the app repository. Each app has its own `config.yaml`, `Dockerfile`, version and runtime entrypoint. Do not introduce a monorepo-wide version number.

## Required changes before a release

1. Update the app's `config.yaml` version, any source-code version constant, its README and CHANGELOG together. Search for remaining references to the old version. Keep the main README's app list, names and versions synchronized with the manifests.
2. Preserve the repository's established Asgard footer and Buy Me a Coffee badge in the root and app READMEs.
3. Use a clear, scoped commit message such as `fix(ha_full_mcp): v1.11.1 — enforce tool permissions`, when a version is being released.
4. Run the relevant CI checks and inspect the results. For behavior or permission changes, test with a non-critical Home Assistant installation before deployment.
5. Publish separate, namespaced tags for apps, following [RELEASING.md](RELEASING.md). A version or a passing test alone does not mean a release has been deployed.

## Building and running

The apps run as containers built by Home Assistant Supervisor. Their Dockerfiles specify Home Assistant base images (check the current Dockerfile rather than relying on a hard-coded image version here).

To build the Full MCP app locally, for example:

```bash
docker build -t asgard-ha-full-mcp ./ha_full_mcp
```

Some operations require Home Assistant Supervisor and cannot be reproduced fully outside Home Assistant. For quick checks, use:

```bash
python -m compileall -q baby_tracker home_stock ha_addons/src ha_full_mcp/src
python -m unittest discover -s ha_full_mcp/tests -p 'test_*.py' -v
python -m unittest discover -s ha_addons/tests -p 'test_*.py' -v
```

Install dependencies for the relevant app in a virtual environment first. Lifeboat's integration-oriented tests may start temporary local HTTP listeners and require `httpx-sse`. The repository's [CI workflow](../.github/workflows/ci.yml) is the source of truth for exact automated commands and outcomes.

## MCP server architecture

Both MCP servers expose SSE and Streamable HTTP transports (check `src/server.py` and `src/routes.py` for actual route behavior). Home Assistant app options are loaded from `/data/options.json` and/or environment variables into `src/config.py`.

For the Full MCP server, tool configuration is mapped in `src/config.py` and the tool definitions. Every new configurable tool must have consistent `config.yaml` schema and defaults, configuration mapping, tool registration, and execution routing. **Disabled tools must be rejected by the execution handler, not merely omitted from the tool listing.** Cover both listing and invocation in tests.

MCP servers can administer Home Assistant. Prefer header-based API key authentication, restrict network access, and review each new route's authorization. API keys passed in paths or query strings can be captured in proxy logs. The `/health` endpoint is intentionally unauthenticated; never treat wildcard CORS settings as an authentication boundary. See [SECURITY.md](../SECURITY.md) and [security review](SECURITY_REVIEW.md).

The Lifeboat is intentionally independent of the Full MCP app. Its recovery features depend on the host, network, Supervisor, and Lifeboat itself still operating. Keep backups and a manual recovery route.

## Baby Tracker and Home Stock

The household apps use FastAPI, SQLite and persistent Home Assistant data storage. When updating database schemas, inspect the actual startup migration approach and preserve existing data. Keep time zone handling, timestamp formatting, and client/server behavior consistent when changing scheduling or tracking logic.

## Collaboration and attribution

Use the actual author's or contributor's Git identity, and preserve legitimate human co-author attribution. Do not invent contributors or append service-session links, credential fragments, or generated tool metadata to commit messages. Avoid rewriting history unless specifically authorized and a recovery reference is preserved.

Changes to secrets, authentication, ports, app privileges, backup/restore behavior, or runtime entrypoints should be isolated from documentation changes and reviewed separately. Report tests only when they have actually run; disclose any failing checks.
