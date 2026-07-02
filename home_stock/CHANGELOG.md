# Changelog

All notable changes to Home Stock will be documented in this file.

## [1.0.0] - 2026-07-02

### Added
- Initial release 🎉
- Tap-to-adjust household stock with quantity steppers and per-item "low" thresholds.
- Automatic shopping list for items at or below their threshold.
- Preset catalog (~80 common Dutch household products) grouped by category, plus custom add.
- Push the shopping list to a Home Assistant to-do list via `todo.add_item` (with duplicate skipping) and an in-app list picker.
- Home Assistant sensors: `sensor.home_stock_shopping_count`, `sensor.home_stock_out_of_stock`, `sensor.home_stock_total_items`.
- Dutch / English UI with one-tap toggle.
- Mobile-first design with automatic dark mode.
- Data model prepared for future barcode scanning (`barcode` column + stock log).
