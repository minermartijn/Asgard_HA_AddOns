# Changelog

## 0.1.0 (2026-11-12)

- Initial release of **ASGARD RainBreak** (`asgard_rain_break`).
- Smart Walk & Bike Break Window Optimizer that scans before, during, and after scheduled breaks (e.g. `10:00` 15m, `12:30` 30m, `15:00` 15m) to recommend the best dry slot.
- High-resolution precipitation engine combining **Buienradar 5-minute radar** (NL/BE) and **Open-Meteo 15-minute/hourly** forecasts (worldwide & extended horizon).
- Per-user activation and automatic Home Assistant `person.*`, `zone.*`, and `notify.*` discovery.
- Per-user Location Mode selector: **Auto Live HA Person Location** (with fallback), **Single Preset Location**, or **Multi-Location Watch**.
- Flexible Time & Urgency engine supporting **Urgent Between Times / Neutral Outside**, **Only Between Times**, and **24/7 Always Active**.
- Dual notification channels: **Home Assistant Notify** and **Pushover API** (Application API Token + User API Key with Urgent/Neutral priority mapping).
- Responsive Ingress web interface (320px mobile to desktop) with interactive precipitation timeline and weather scenario simulator.
