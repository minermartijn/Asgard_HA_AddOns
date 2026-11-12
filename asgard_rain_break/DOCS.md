# ASGARD RainBreak — Documentation

## Overview

**ASGARD RainBreak** (`v0.2.0`) combines real-time 5-minute precipitation radar with a smart scheduling engine designed around real daily routines: walking during work breaks, cycling commutes, and outdoor activities.

## 1. Setting Up Household Users & Per-User Activation

1. Open the **Users & Channels** tab and click **↻ Sync from Home Assistant**.
2. RainBreak discovers your Home Assistant `person.*` entities, `zone.*` locations, and `notify.*` actions.
3. Each user profile has an independent **Activate User / Pause User** button:
   - If your Home Assistant instance has 2 users, you can keep only your own profile **Active** and leave the second user **Paused** until you want to configure them later.

## 2. Location Tracking Modes & 1-Click Zone Import

For each user profile, open **Configure** and choose one of three location modes:

- **Auto: Use Live HA Person GPS Location (`live_person`)**:
  - Reads the live `latitude` and `longitude` attributes from your linked Home Assistant `person.<name>` entity (updated by the Home Assistant Companion App on your phone).
  - The High-Resolution Precipitation Timeline graph at the bottom of the dashboard automatically defaults to this live GPS location, showing real-time 5-minute radar points wherever you are.
  - If your `person.*` entity temporarily lacks GPS coordinates, RainBreak automatically falls back to your selected **Fallback Location**.
- **Single Preset Location (`fixed_location`)**:
  - Always monitors a specific saved location (such as *Work / Office* or *Home*).
- **Multi-Location Watch (`multi_location`)**:
  - Monitors all checked preset locations simultaneously.

### 1-Click Import from Home Assistant

On the **Locations & Zones** tab:
- Every discovered Home Assistant zone card offers instant **+ Add as Saved Location**, **🏢 Set as Work**, and **🏠 Set as Home** buttons—no manual coordinate copy-pasting required.
- In the **+ Add Location** modal, select any zone or person from the **⚡ 1-Click Import from Home Assistant** dropdown to auto-populate coordinates.

## 3. Time Windows & Urgency Rules (`Urgent` vs. `Neutral`)

Each user profile supports three schedule modes:

1. **Urgent Between Times, Neutral Outside (`urgent_window_else_neutral`)**:
   - During your configured window (for example `07:30` to `17:30`, Mon–Fri), alerts are dispatched as **Urgent** (high-priority mobile push / Pushover Priority `1`).
   - Outside that window, alerts are still delivered but automatically downgraded to **Neutral** (standard priority).
2. **Only Between Times (`active_window_only`)**:
   - Alerts are only dispatched inside the configured time window and suppressed outside it.
3. **Always Active (`always`)**:
   - Alerts are dispatched 24/7 using your default urgency setting.

## 4. Configuring Break, Commute & Activity Windows

Open the **Break Windows** tab:

- Click **🚲 Commute + Workday Routine** to automatically create:
  - **08:00 Morning Bike Ride to Work** (`30 min` duration, bike commute advice, alternative transit tips)
  - **10:00 Morning Break Walk** (`15 min` duration, work-only geofence)
  - **12:30 Lunch Walk / Bike Ride** (`30 min` duration, work-only geofence)
  - **15:00 Afternoon Break Walk** (`15 min` duration, work-only geofence)
  - **17:00 Evening Ride Home** (`30 min` duration, bike commute advice)
- Or click **⚡ Workday Breaks (10:00 · 12:30 · 15:00)** to load standard midday work breaks.
- Or click **+ Add Break Window** to customize:
  - **Activity Type**: Choose between `🚶 Walk`, `🚲 Bike Ride`, `🚲 Bike Commute`, `🏃 Run`, `🐕 Dog Walk`, and `☕ Outdoor Break`.
  - **Location Geofence Condition**:
    - **Active Anywhere (No Geofence)**: Always evaluates regardless of where you are.
    - **Only Active When AT Location (e.g. Work)**: Pauses alerts when you are at home (e.g. sick or working from home), with a clear `PAUSED · NOT AT LOCATION` status badge.
    - **Only Active When AWAY from Location (e.g. Away from Home)**: Only alerts when you are out of the house.
  - **Planned Start Time & Duration**: When your break normally starts and how long it lasts.
  - **Can Leave Earlier By / Can Shift Later By**: How many minutes before or after your scheduled break RainBreak should search for a dry slot.
  - **Alert Lead Time**: How many minutes before the window RainBreak should evaluate the radar and send you a notification.

## 5. Notification Systems: Home Assistant Notify & Pushover

You can enable one or both notification systems per user:

- **Home Assistant Notify**:
  - Select one or more discovered `notify.mobile_app_*` or `notify.*` targets.
- **Pushover**:
  - Enter your **Pushover Application API Token** (either once in **Settings & Audit Log → Global Pushover App API Token** or per user) and the user's **Pushover User / Group Key**.
  - Choose the Pushover sound and whether **Urgent** alerts use Pushover Priority `1` (High Priority, bypasses quiet hours) or Priority `2` (Emergency).
