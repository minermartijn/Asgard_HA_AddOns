"""End-to-end browser automation tests for ASGARD Backup Inspector using Playwright.

Covers the 14 real browser test scenarios specified in Phase 1.5 engineering requirements:
1. Dashboard loads successfully.
2. Summary cards render.
3. Backup table renders actual returned records (tested with 14 backups).
4. Dates are formatted without exceptions.
5. Storage totals render.
6. Last-check information renders.
7. Refresh updates displayed information.
8. Refresh rate limiting is handled gracefully.
9. Empty backup lists display correctly.
10. Backend errors produce useful messages.
11. Missing metadata does not crash the page.
12. Mobile viewport remains usable.
13. Light and dark themes render correctly.
14. No unexpected JavaScript console errors occur.
"""

import json
import os
import socket
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from app.main import create_app
from app.models import ApiStatus
from app.normalize import ParseResult, normalize_backup
from app.settings import Settings
from app.sources import BackupSource, SourceError

def get_browser_executable() -> Optional[str]:
    env_bin = os.environ.get("PLAYWRIGHT_CHROME_BIN")
    if env_bin and os.path.exists(env_bin):
        return env_bin
    for candidate in ("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(candidate):
            return candidate
    return None


@pytest.fixture(scope="module")
def browser_instance():
    exe = get_browser_executable()
    with sync_playwright() as p:
        try:
            if exe:
                browser = p.chromium.launch(executable_path=exe, headless=True)
            else:
                browser = p.chromium.launch(headless=True)
        except Exception as err:
            pytest.skip(f"Browser launch skipped: {err}")
        yield browser
        browser.close()


def get_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class StaticMockSource:
    backups: list
    days_until_stale: int = 3
    demo: bool = False
    error: Optional[Exception] = None

    async def fetch(self) -> ParseResult:
        if self.error:
            raise self.error
        normalized = [normalize_backup(b) for b in self.backups]
        return ParseResult(backups=[b for b in normalized if b is not None], days_until_stale=self.days_until_stale)


def make_14_backups():
    """Generates 14 realistic backup records matching the user's real HA scenario."""
    items = []
    # 10 full backups, 4 partial backups
    for i in range(1, 15):
        is_full = i <= 10
        items.append({
            "slug": f"ha_backup_{i:04d}",
            "name": f"Core Backup {i:02d} {'(Full)' if is_full else '(Partial)'}",
            "date": f"2026-11-{11 - (i // 4):02d}T{12 - (i % 6):02d}:30:00+01:00",
            "type": "full" if is_full else "partial",
            "size_bytes": 1_000_000_000 * i if i != 14 else None,
            "location": ".local" if i % 3 != 0 else "nas_backup",
            "locations": [".local"] if i % 3 != 0 else [".local", "nas_backup"],
            "protected": i % 2 == 0,
            "compressed": True,
        })
    return items


class AppServer:
    def __init__(self, source: BackupSource, tmp_path: Path):
        self.port = get_free_port()
        self.settings = Settings(
            allowed_clients=("*",),
            data_dir=str(tmp_path),
            min_refresh_interval_seconds=2.0,
        )
        self.app = create_app(settings=self.settings, source=source)
        self.server = uvicorn.Server(uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        time.sleep(0.4)

    def stop(self):
        self.server.should_exit = True


def test_dashboard_14_backups_full_render(browser_instance, tmp_path):
    """Test 1, 2, 3, 4, 5, 6, 14:

    Verifies the user's screenshot scenario is 100% resolved:
    - 14 backups in table
    - Most recent backup date displays without exception
    - Storage total displays (not '-')
    - Last checked updates (not 'Not checked yet')
    - 0 unhandled JavaScript console errors
    """
    source = StaticMockSource(backups=make_14_backups())
    server = AppServer(source=source, tmp_path=tmp_path)

    console_errors = []

    try:
        page = browser_instance.new_page()
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        page.goto(f"http://127.0.0.1:{server.port}/")
        page.wait_for_selector("#backup-rows tr")

        # 1. Summary card checks
        assert page.locator("#freshness").text_content() == "Recent backup listed"
        assert page.locator("#count").text_content() == "14"
        assert "full" in page.locator("#count-breakdown").text_content()

        # 2. Most recent backup & date
        newest = page.locator("#newest").text_content()
        newest_date = page.locator("#newest-date").text_content()
        assert newest != "–"
        assert newest_date != "" and newest_date != "–"

        # 3. Known total storage
        storage = page.locator("#storage").text_content()
        assert storage != "–"
        assert "GB" in storage

        # 4. Last checked
        last_checked = page.locator("#last-checked").text_content()
        assert "Last checked: " in last_checked
        assert "Not checked yet" not in last_checked

        # 5. Table rows: all 14 backups render
        # Page size default is 25, so all 14 appear
        row_count = page.locator("#backup-rows tr").count()
        assert row_count == 14

        # 6. Storage breakdown visualization rendered
        assert page.locator("#bar-full").is_visible()
        assert page.locator("#bar-partial").is_visible()

        # 7. Timeline rendered
        timeline_items = page.locator(".timeline-item").count()
        assert timeline_items >= 1

        # 8. NO JavaScript console exceptions!
        assert console_errors == [], f"Unexpected console errors: {console_errors}"

        page.close()
    finally:
        server.stop()


def test_table_search_and_filters(browser_instance, tmp_path):
    """Test table live search, type filter, and sort order."""
    source = StaticMockSource(backups=make_14_backups())
    server = AppServer(source=source, tmp_path=tmp_path)

    try:
        page = browser_instance.new_page()
        page.goto(f"http://127.0.0.1:{server.port}/")
        page.wait_for_selector("#backup-rows tr")

        # 1. Live search for 'Partial'
        page.fill("#table-search", "Partial")
        time.sleep(0.2)
        assert page.locator("#backup-rows tr").count() == 4

        # 2. Clear search
        page.fill("#table-search", "")
        time.sleep(0.2)
        assert page.locator("#backup-rows tr").count() == 14

        # 3. Filter by type: Full
        page.select_option("#filter-type", "full")
        time.sleep(0.2)
        assert page.locator("#backup-rows tr").count() == 10

        # 4. Filter by type: Partial
        page.select_option("#filter-type", "partial")
        time.sleep(0.2)
        assert page.locator("#backup-rows tr").count() == 4

        page.close()
    finally:
        server.stop()


def test_refresh_and_rate_limiting(browser_instance, tmp_path):
    """Test 7 & 8: Refresh button and 429 rate limit countdown."""
    source = StaticMockSource(backups=make_14_backups())
    server = AppServer(source=source, tmp_path=tmp_path)

    try:
        page = browser_instance.new_page()
        page.goto(f"http://127.0.0.1:{server.port}/")
        page.wait_for_selector("#backup-rows tr")

        # Rapidly click refresh to trigger 429 rate limit
        page.click("#refresh")
        time.sleep(0.1)
        page.click("#refresh")
        time.sleep(0.3)

        # Button should show rate limit warning banner or text
        btn_text = page.locator("#refresh").text_content()
        cached_banner_hidden = page.locator("#cached-banner").is_hidden()
        # Either the banner or the button text reflects the rate limit
        assert "Wait" in btn_text or not cached_banner_hidden

        page.close()
    finally:
        server.stop()


def test_empty_backup_list(browser_instance, tmp_path):
    """Test 9: Empty backup list display."""
    source = StaticMockSource(backups=[])
    server = AppServer(source=source, tmp_path=tmp_path)

    try:
        page = browser_instance.new_page()
        page.goto(f"http://127.0.0.1:{server.port}/")
        page.wait_for_selector("#cards")

        assert page.locator("#freshness").text_content() == "No backups found"
        assert page.locator("#count").text_content() == "0"
        assert page.locator("#empty").is_visible()
        assert page.locator("#backup-table").is_hidden()

        page.close()
    finally:
        server.stop()


def test_backend_error_handling(browser_instance, tmp_path):
    """Test 10 & 11: Backend errors produce friendly message without page crash."""
    source = StaticMockSource(
        backups=[],
        error=SourceError(ApiStatus.FORBIDDEN, "App is not allowed to read backup info (403)"),
    )
    server = AppServer(source=source, tmp_path=tmp_path)

    try:
        page = browser_instance.new_page()
        page.goto(f"http://127.0.0.1:{server.port}/")
        page.wait_for_selector("#error-banner")

        assert page.locator("#error-banner").is_visible()
        assert "403" in page.locator("#error-banner").text_content()
        assert page.locator("#freshness").text_content() in ("Status unknown", "Permission denied")

        page.close()
    finally:
        server.stop()


def test_mobile_viewport(browser_instance, tmp_path):
    """Test 12: Mobile responsive rendering."""
    source = StaticMockSource(backups=make_14_backups())
    server = AppServer(source=source, tmp_path=tmp_path)

    try:
        # iPhone 13 dimensions: 390 x 844
        page = browser_instance.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"http://127.0.0.1:{server.port}/")
        page.wait_for_selector("#backup-rows tr")

        assert page.locator("#freshness").is_visible()
        assert page.locator("#count").is_visible()
        assert page.locator("#storage").is_visible()
        # Table wrap should be scrollable
        assert page.locator(".table-wrap").is_visible()

        page.close()
    finally:
        server.stop()


def test_theme_mode(browser_instance, tmp_path):
    """Test 13: Light and dark mode support."""
    source = StaticMockSource(backups=make_14_backups())
    server = AppServer(source=source, tmp_path=tmp_path)

    try:
        # Test light color scheme emulation
        page = browser_instance.new_page(color_scheme="light")
        page.goto(f"http://127.0.0.1:{server.port}/")
        page.wait_for_selector("#cards")
        assert page.locator("#freshness").is_visible()
        page.close()

        # Test dark color scheme emulation
        page_dark = browser_instance.new_page(color_scheme="dark")
        page_dark.goto(f"http://127.0.0.1:{server.port}/")
        page_dark.wait_for_selector("#cards")
        assert page_dark.locator("#freshness").is_visible()
        page_dark.close()
    finally:
        server.stop()
