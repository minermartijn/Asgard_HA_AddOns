# Changelog

All notable changes to ASGARD NotifyHub will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-11-11

### Fixed
- **Ingress API Route Resolution:** Added centralized `getApiUrl()` resolver so all frontend API requests preserve the `/api/hassio_ingress/<session>/` prefix, eliminating HTTP 404 errors when accessed via the Home Assistant sidebar.
- **Frontend / Backend Contract Alignment:** Added `discovered_services_count` and `blocked_quiet_hours_24h` contract alignment and backward-compatible aliases (`services_discovered`, `quiet_silenced_24h`).
- **HA Service Discovery & Status Detail:** Enhanced service discovery to discover both classic notify services and modern `notify.*` entity targets via `/states`, with descriptive error messages when credentials are missing or the API returns 401/403.
- **Demo Mode Isolation:** Fixed bug where missing Supervisor tokens would silently place the application into demo mode; now explicitly reports disconnected state unless demo mode is configured.
- **Ingress Security:** Hardened source-IP checks and eliminated forged `X-Ingress-Path` header bypass vulnerability.
- **Route Action Dropdown:** Corrected service naming binding in the Add Route dialog (`ha_domain` and `ha_service`).
- **Global Policy Support:** Added `TargetType.GLOBAL` to support household-wide quiet hour policies.
- **Ingress Regression Testing:** Added mandatory Playwright Ingress path regression tests asserting that zero requests escape the Ingress session prefix.

## [0.1.0] - 2026-11-11

### Added
- Initial release of ASGARD NotifyHub.
- Centralized notification routing and policy management dashboard accessible via Home Assistant Ingress on port 8098.
- Recipient and Route management supporting individual household members mapped to multiple Home Assistant notification services.
- Logical Recipient Groups.
- Timezone-aware Quiet Hours policy engine with cross-midnight support, day-of-week masks, and explicit urgent overrides.
- Priority-based dispatch (`informational`, `normal`, `urgent`).
- Dry-run preview simulation (`POST /api/send/preview`) and execution (`POST /api/send`).
- Deduplication and idempotency controls.
- In-process SQLite delivery audit trail (`/data/notifyhub.db`) with automatic 30-day purge.
- Strict security allowlist restricting Core API calls to `notify` and `persistent_notification` domains.
- Full automated test suite (37 tests across unit, integration, and Playwright browser).
