# Changelog

All notable changes to ASGARD Backup Inspector will be documented in this file.

## [0.3.0] - 2026-11-11

### Added
- **Multi-Location Backup Discovery:** Discovers and aggregates backups stored in Home Assistant (`GET /backups/info`) alongside backups synchronized with the third-party Home Assistant Google Drive Backup add-on via `sensor.backup_state`.
- **Deduplication Engine:** Confidently merges replicated archives by matching canonical slugs, avoiding double-counting storage or duplicate records.
- **Remote-Only Backups:** Discovers and displays cloud-only archives stored in Google Drive that have been rotated or deleted locally.
- **Backup Redundancy Matrix:** Independent status evaluations for Local Freshness, Cloud Freshness, Off-Site Coverage (Confirmed, Incomplete, None), and Full-Backup Coverage (Present, Stale, Not Detected).
- **Google Drive Overview Card:** Live cloud sync state, backups stored in Drive, last upload timestamp, cloud storage usage, and available free space.
- **Location Filtering:** Filter table records by *All Locations*, *Both (Local + Drive)*, *Local Only*, *Google Drive Only*, or *Pending Upload*.
- **Multi-Provider Architecture:** Decoupled `SupervisorBackupProvider`, `GoogleDriveBackupProvider`, and `BackupAggregator` with independent failure isolation.
- **Permission Boundary Documentation:** Added `homeassistant_api: true` strictly to query `sensor.backup_state` via read-only GET requests without write access.

## [0.2.0] - 2026-11-11

### Fixed
- Fixed critical frontend `TypeError` in `formatDate()` where combining `dateStyle`/`timeStyle` with `timeZoneName` halted rendering, preventing the storage card, last-checked timestamp, and backup table from populating.
- Added safe formatting fallbacks and isolated rendering per dashboard card so unexpected values in one record never block the rest of the interface.

### Added
- **Storage Visualization:** Full backup vs Partial backup storage breakdown bar, location distribution badges (`.local`, remote mounts), and top backup storage details.
- **Backup Timeline:** Chronological visual timeline of recent backups displaying backup types and age relative to freshness threshold.
- **Table Controls:** Real-time search by backup name or ID, filters for backup type (all/full/partial), storage location, and password protection status.
- **Table Sorting & Pagination:** Clickable column headers and sort selector (Date, Size, Name, Type) with page size selection (10, 25, 50, all).
- **Diagnostics Panel:** Expandable panel with Ingress verification, Supervisor status, cache policy, and threshold details.
- **Measured History Snapshots:** Safe, crash-resistant snapshot history stored under `/data/history.json` with rate-limited dedup and SVG trend visualization.
- **Automated Browser Tests:** Real Playwright end-to-end browser test suite verifying rendering, responsive viewports, light/dark themes, and console clean state.

## [0.1.0] - 2026-11-11

### Added
- Initial release with read-only Supervisor adapter for `GET /backups/info`.
- Normalized backup metadata and freshness evaluation engine.
- Home Assistant Ingress web interface.
