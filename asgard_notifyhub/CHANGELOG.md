# Changelog

## 0.1.5 - 2026-11-11

### Added
- **Honest Dispatch Outcome Aggregation (`DispatchSummary`)**: `/api/send` and the Composer now aggregate and distinguish `submitted`, `blocked_quiet_hours`, `suppressed_duplicate`, `blocked_priority`, `route_disabled`, `recipient_disabled`, `invalid_route`, and `failed`. Suppressed or failed notifications are never labeled as "Dispatched", mixed results show a warning with a per-status breakdown, and submission to Home Assistant is clearly distinguished from physical device delivery.
- **Segmented Target Scope Selector (`Single Recipient | Group | Everyone`)**: Replaced the confusing target dropdown with an accessible segmented control that shows only the active selector, disables and hides inactive selectors (`[hidden] { display: none !important; }`), explains broadcast scope for `Everyone`, and displays a live `"Sending to: …"` confirmation bar.
- **Full Mobile Responsiveness (320px–1024px+) & Mobile Audit History Cards**: Redesigned CSS layout with responsive grids, wrapping code pills, touch-friendly controls, a responsive 6-tab navigation grid on narrow viewports, and stacked mobile audit history cards (`<= 720px`) alongside the desktop table.
- **Policy & Route Editing + Orphaned Policy Detection**: Added Edit modals for both Quiet Hours policies and Routes, detects policies referencing deleted recipients/groups (`Orphaned Target`), and validates targets and IANA timezones before saving.
- **Action-Level Notification Allowlist**: Explicitly excludes non-delivery actions (`persistent_notification.dismiss`, `persistent_notification.dismiss_all`, and standalone `notify.send_message`) from discovery, route creation, and dispatch, while validating stored routes prior to execution.
- **Galaxy Watch / Companion Entity Diagnostics**: Deterministic single-request dispatch (never retrying failed requests across alternative services, preventing duplicate alerts), clean `notify.send_message` payload construction, and actionable error messages recommending `notify.mobile_app_<device>` when a companion `notify.<device>` entity returns HTTP 500.
- **`Europe/Amsterdam` Timezone Support & Presets**: Included `tzdata` and IANA timezone validation with `Europe/Amsterdam` (CET/CEST, DST transitions) as the default for new installations and quick-select presets in recipient and policy modals while preserving existing `UTC` policies.

## 0.1.4 - 2026-11-11

### Fixed
- **Modal Select Dropdown Auto-Close Bug**: Resolved issue where selecting options in dropdowns (e.g. Route Target Action, Minimum Priority) inside `#app-modal` prematurely closed the dialog. Replaced coordinate bounding box checks with explicit backdrop overlay target detection (`e.target === el.appModal && !e.target.closest('.modal-content')`), keeping all modals open during dropdown selection.
- **Home Assistant Modern Notify Entity Dispatch (HTTP 400)**: Resolved `Home Assistant rejected call with HTTP 400: 400: Bad Request` when dispatching to modern notification entities like `notify.mart_s25`. NotifyHub now automatically routes entity targets through `notify.send_message` with `entity_id` (and includes automatic bidirectional fallback for legacy services), ensuring smooth delivery to all modern mobile app and companion device entities.
- **Cache-Busting Assets**: Bumped asset cache-busting queries to `?v=0.1.4`.


## 0.1.3 - 2026-11-11

### Fixed
- **Static Assets 404 Under Ingress**: Removed `request.scope["root_path"]` modification in HTTP middleware that caused Starlette `StaticFiles` Mount to fail routing on `/static/app.css` and `/static/app.js` when Home Assistant sends `X-Ingress-Path`. Static assets now reliably return 200 OK.
- **Cache-Busting Assets**: Bumped asset cache-busting queries to `?v=0.1.3`.


## 0.1.2 - 2026-11-11

### Fixed
- **Ingress Base & Token Resolution**: Injected dynamic `<base href="...">` and `window.__INGRESS_BASE__` based on Home Assistant's `X-Ingress-Path` header, guaranteeing all API endpoints (`api/recipients`, `api/history`, `api/summary`) resolve within the Ingress session even when the iframe or external URL lacks a trailing slash.
- **Root Path & Redirect Security**: Configured ASGI `root_path` and automatic `Location` header rewrites in Ingress middleware to prevent 307 redirects from escaping to Home Assistant Core's root domain.
- **Cache-Busting & Aggressive Cache Control**: Added `Cache-Control: no-cache, no-store, must-revalidate` and cache-busting query strings (`?v=0.1.2`) to frontend assets to prevent stale browser caches.
- **Unbuffered Logging & Access Logs**: Added `PYTHONUNBUFFERED=1` to container environment and `--access-log` with unbuffered Python (`-u`) to `run.sh`, ensuring all requests and errors are immediately visible in Home Assistant App logs.


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
