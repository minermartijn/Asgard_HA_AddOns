# Changelog

All notable changes to ASGARD Backup Inspector will be documented in this file.

## [Unreleased]

## [0.1.0] - not yet released

### Added
- Read-only Supervisor adapter for `GET /backups/info`, with timeouts, response size limits and clear handling of 401/403/5xx/malformed responses.
- Normalized backup metadata where unknown values stay unknown (no size becomes "Unknown", never 0).
- Freshness evaluation with a configurable threshold; "No backups found" is never reported as healthy.
- Ingress-only dashboard with overview cards and a backup table, relative URLs, no external assets, light/dark theme.
- 5-minute metadata cache, rate-limited manual refresh, last-good data kept on failure.
- `demo_mode` option with clearly labelled synthetic data.
