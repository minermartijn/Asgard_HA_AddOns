# Changelog

All notable changes to ASGARD NotifyHub will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
