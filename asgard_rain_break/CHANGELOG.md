# Changelog

## 0.2.0 (2026-11-12)

- **Default Live GPS Forecast & Prominent Pills**: The high-resolution precipitation timeline graph now defaults automatically to the active user's Live HA Location (`live_<user_id>`), placing live GPS pills at the front with glowing indicator styling and pulse animation.
- **Location Geofencing & Work-Only Break Windows**: Added `LocationRequirementMode` (`any_location`, `only_at_location`, `only_away_from_location`). Work break windows (e.g. 10:00 / 12:30 / 15:00) automatically detect when the user is away from the work zone or GPS boundary and gracefully pause alerts with a clear `PAUSED · NOT AT LOCATION` status badge.
- **1-Click Home Assistant Entity Import**:
  - Direct 1-click `+ Add as Saved Location`, `🏢 Set as Work`, and `🏠 Set as Home` actions on discovered HA Zone and Person cards.
  - Quick-fill dropdown inside the Add Location modal to instantly populate name, latitude, longitude, and HA zone entity from discovered entities without manual copy-pasting.
  - Backend endpoint `POST /api/locations/import-ha` for seamless integration.
- **Commute & Outdoor Routine Support**:
  - Expanded activity types: `🚲 Bike Commute`, `🚶 Walk`, `🚲 Bike Ride`, `🏃 Run`, `🐕 Dog Walk`, and `☕ Outdoor Break`.
  - Commute-specific advice: advises earlier/later departure or switching to car/transit when heavy showers hit during commute hours.
  - Added `🚲 Load Commute + Workday Routine` preset button (08:00 Bike Commute, 10:00/12:30/15:00 Work Breaks, 17:00 Ride Home).
- **Buienradar Redirect Handling**: Enabled `follow_redirects=True` and custom User-Agent in HTTP client for Buienradar 5-min radar API to ensure reliable direct radar parsing.

## 0.1.0 (2026-11-12)

- Initial release of **ASGARD RainBreak** (`asgard_rain_break`).
- Smart Walk & Bike Break Window Optimizer that scans before, during, and after scheduled breaks (e.g. `10:00` 15m, `12:30` 30m, `15:00` 15m) to recommend the best dry slot.
- High-resolution precipitation engine combining **Buienradar 5-minute radar** (NL/BE) and **Open-Meteo 15-minute/hourly** forecasts (worldwide & extended horizon).
- Per-user activation and automatic Home Assistant `person.*`, `zone.*`, and `notify.*` discovery.
- Per-user Location Mode selector: **Auto Live HA Person Location** (with fallback), **Single Preset Location**, or **Multi-Location Watch**.
- Flexible Time & Urgency engine supporting **Urgent Between Times / Neutral Outside**, **Only Between Times**, and **24/7 Always Active**.
- Dual notification channels: **Home Assistant Notify** and **Pushover API** (Application API Token + User API Key with Urgent/Neutral priority mapping).
- Responsive Ingress web interface (320px mobile to desktop) with interactive precipitation timeline and weather scenario simulator.
