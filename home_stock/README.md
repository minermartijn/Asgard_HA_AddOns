# 🧺 Home Stock

Beautiful, low-friction household stock & shopping tracker for Home Assistant.
Built for the whole family — the everyday action is a single tap on **−** or **+**.
No accounts, no clutter, no learning curve.

## ✨ Features

- **Tap-to-adjust stock** — every product is a card with a quantity stepper. Tap **−** when you use something, **+** when you restock.
- **Automatic shopping list** — anything at or below its "warn at" threshold appears on the **Boodschappen / Shopping** tab automatically. Nothing to remember.
- **Preset catalog** — add common Dutch household products (food, cleaning, toiletries, paper goods, baby, pet, batteries…) from a tappable grid, or type your own.
- **Sends to Home Assistant's own list** — push the shopping list straight into any HA **to-do / shopping list** (`todo.add_item`), so it shows up on your phone and dashboards. Duplicates are skipped.
- **HA sensors** — exposes `sensor.home_stock_shopping_count`, `sensor.home_stock_out_of_stock`, and `sensor.home_stock_total_items` (with an `items` attribute) for your own automations and dashboards.
- **Dutch & English** — one-tap language toggle.
- **Gorgeous & mobile-first** — phone-width UI, soft cards, automatic dark mode.

## 🚀 Installation

1. Add this repository to Home Assistant (**Settings → Add-ons → Add-on Store → ⋮ → Repositories**):
   `https://github.com/minermartijn/Asgard_HA_AddOns`
2. Install **Home Stock** and start it.
3. Open the **Voorraad** panel from the sidebar.

## ⚙️ Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `language` | `nl` | UI language (`nl` / `en`). |
| `household_name` | `""` | Shown in the header. |
| `todo_entity` | `todo.shopping_list` | Which HA to-do list the shopping list is sent to. Also selectable in-app. |
| `auto_sync_todo` | `false` | When on, new low/out items are pushed to the HA to-do list automatically (already-present items are skipped) — no need to press the button. |
| `expose_sensors` | `true` | Publish `sensor.home_stock_*` to Home Assistant. |

Data is stored in `/data/db/home_stock.db` and survives restarts and updates.

## 🔭 Roadmap

- 📷 **Barcode scanning** — scan a product to restock it in one tap and attach barcodes to known products. The data model is already prepared for it.

---
Built with ⚡ by Asgard.

### Support my caffeine addiction ☕
If this add-on saved you a trip back to the store, feel free to fuel my next coding session! My code is powered by high-quality caffeine—one cup equals approximately three features and only one new bug. 😉

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/minermartijn)
