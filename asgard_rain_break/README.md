# ASGARD RainBreak

**Smart rain radar alerts, walk & bike break window optimizer, multi-location tracking, and Home Assistant / Pushover notifications.**

ASGARD RainBreak is a Home Assistant App that monitors high-resolution precipitation forecasts (**Buienradar 5-minute radar** in the Netherlands/Belgium combined with **Open-Meteo 15-minute/hourly** forecasts worldwide) and advises you **when to leave earlier or later** for your daily breaks, walks, or bike rides so you stay dry.

## Key Features

- **Smart Break & Walk Window Optimizer**:
  - Configure your daily breaks or outdoor activities (for example: **10:00 for 15 min**, **12:30 for 30 min**, and **15:00 for 15 min**) along with how many minutes *earlier* or *later* you are flexible to go.
  - When rain is forecasted during a scheduled break, RainBreak automatically scans before and after your break and recommends the nearest dry window (e.g. *"☔ Rain expected during your 10:00 Walk (2.4 mm/h). 💡 Leave 15 min earlier: 09:45–10:00 is completely dry!"*).
  - If your planned break is dry right now but rain arrives immediately after, RainBreak warns you to leave on time and not delay.
- **Per-User Activation & Auto Live Location**:
  - Automatically discovers `person.*` entities from Home Assistant.
  - Activate or pause monitoring independently **per household user** (for example, enable alerts only for yourself right now, and enable a second household member later with one click).
  - Choose per user between:
    1. **Auto (Live HA User Location)**: Dynamically tracks the live GPS coordinates of the user's `person.*` entity in Home Assistant (with a configurable fallback location).
    2. **Single Preset Location**: Monitors a fixed saved location such as *Work / Office* or *Home*.
    3. **Multi-Location Watch**: Monitors multiple saved locations simultaneously.
- **Flexible Time Schedules & Urgency Rules (`Urgent` vs. `Neutral`)**:
  - **Urgent Between Times, Neutral Outside**: Send high-priority **Urgent** alerts during work/daytime hours (e.g. `07:30–17:30`), and automatically downgrade alerts to **Neutral** outside those hours.
  - **Only Between Times**: Only send alerts inside the configured time window and silence everything outside.
  - **Always (24/7)**: Always use your chosen default urgency level.
- **Multi-System Notifications (Home Assistant Notify + Pushover)**:
  - **Home Assistant Notify**: Supports `notify.mobile_app_*` companion services, `notify.*` services, and modern `notify.*` entities.
  - **Pushover API**: Built-in direct Pushover integration with **Pushover App API Token** (global or per-user) and **Pushover User/Group Key**, mapping `Urgent` vs. `Neutral` directly to Pushover priority levels and sounds.

## Installation

1. In Home Assistant, open **Settings → Apps → App store → ⋮ → Repositories** and add:
   ```text
   https://github.com/minermartijn/Asgard_HA_AddOns
   ```
2. Install **ASGARD RainBreak**, start the App, and click **Open Web UI** (or enable **Show in sidebar**).
3. See [DOCS.md](DOCS.md) for detailed configuration instructions.

---

Built with ⚡ by Asgard.

### Support my caffeine addiction ☕

If these apps saved you time (or a headache), feel free to fuel my next coding session! My code is powered by high-quality caffeine—one cup equals approximately three features and only one new bug. 😉

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/minermartijn)
