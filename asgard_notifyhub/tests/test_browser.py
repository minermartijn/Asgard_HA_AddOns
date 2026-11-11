"""End-to-end browser automation tests for ASGARD NotifyHub using Playwright."""

import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import pytest
import uvicorn
from playwright.sync_api import sync_playwright

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app.client import DemoHomeAssistantClient
from app.main import create_app
from app.service import NotifyHubService
from app.settings import Settings
from app.storage import Storage


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


class AppServer:
    def __init__(self, tmp_path: Path):
        self.port = get_free_port()
        db_path = tmp_path / "notifyhub_browser.db"
        self.storage = Storage(db_path)
        self.client = DemoHomeAssistantClient()
        self.service = NotifyHubService(storage=self.storage, ha_client=self.client, demo_mode=True)
        self.settings = Settings(
            db_path=db_path,
            allowed_source_ips="127.0.0.1",
            demo_mode=True,
            default_timezone="UTC",
            dedup_window_seconds=60,
        )
        self.app = create_app(settings=self.settings, service=self.service)
        self.server = uvicorn.Server(uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        time.sleep(0.5)

    def close(self):
        self.server.should_exit = True
        self.thread.join(timeout=2.0)


@pytest.fixture(scope="module")
def running_server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("browser_srv")
    srv = AppServer(tmp)
    yield srv
    srv.close()


def test_dashboard_loads_and_has_no_console_errors(browser_instance, running_server):
    page = browser_instance.new_page()
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    page.goto(f"http://127.0.0.1:{running_server.port}/")
    page.wait_for_selector("#stat-ha-conn")

    assert "ASGARD NotifyHub" in page.title()
    assert page.is_visible("#tab-dashboard")
    assert page.inner_text("#stat-ha-conn") in ("Demo Mode", "Connected")
    # Verify discovered services chips render
    page.wait_for_selector(".service-chip")
    chips = page.query_selector_all(".service-chip")
    assert len(chips) >= 3

    assert len(errors) == 0, f"Unexpected JS console errors: {errors}"
    page.close()


def test_tab_navigation(browser_instance, running_server):
    page = browser_instance.new_page()
    page.goto(f"http://127.0.0.1:{running_server.port}/")
    page.wait_for_selector(".nav-tabs")

    # Click Composer tab
    page.click('button[data-tab="tab-composer"]')
    assert page.is_visible("#tab-composer")
    assert not page.is_visible("#tab-dashboard")

    # Click Recipients tab
    page.click('button[data-tab="tab-recipients"]')
    assert page.is_visible("#tab-recipients")

    # Click Groups tab
    page.click('button[data-tab="tab-groups"]')
    assert page.is_visible("#tab-groups")

    # Click Policies tab
    page.click('button[data-tab="tab-policies"]')
    assert page.is_visible("#tab-policies")

    # Click History tab
    page.click('button[data-tab="tab-history"]')
    assert page.is_visible("#tab-history")

    page.close()


def test_composer_preview_and_dispatch(browser_instance, running_server):
    page = browser_instance.new_page()
    page.goto(f"http://127.0.0.1:{running_server.port}/")
    page.click('button[data-tab="tab-composer"]')
    page.wait_for_selector("#comp-message")

    page.fill("#comp-title", "Alert from Browser Test")
    page.fill("#comp-message", "Smoke test ping content")

    # Test Dry-Run Preview
    page.click("#btn-preview-send")
    page.wait_for_selector(".preview-item")
    items = page.query_selector_all(".preview-item")
    assert len(items) >= 1

    # Test Execution
    page.click("#btn-execute-send")
    page.wait_for_selector(".banner-success")
    assert "Dispatched" in page.inner_text(".banner-success")

    # Verify Audit History has entry
    page.click('button[data-tab="tab-history"]')
    page.wait_for_selector("#history-tbody tr")
    rows = page.query_selector_all("#history-tbody tr")
    assert len(rows) >= 1

    page.close()


def test_add_recipient_via_modal(browser_instance, running_server):
    page = browser_instance.new_page()
    page.goto(f"http://127.0.0.1:{running_server.port}/")
    page.click('button[data-tab="tab-recipients"]')
    page.wait_for_selector("#btn-add-recipient")

    page.click("#btn-add-recipient")
    page.wait_for_selector("#rec-name")
    page.fill("#rec-name", "Loki Odinson")
    page.fill("#rec-tz", "Europe/Oslo")
    page.click('#modal-rec-form button[type="submit"]')

    # Wait for recipient card containing Loki Odinson to render
    page.wait_for_function('() => document.body.innerText.includes("Loki Odinson")')
    assert "Loki Odinson" in page.content()

    page.close()


def test_mobile_viewport_rendering(browser_instance, running_server):
    page = browser_instance.new_page()
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(f"http://127.0.0.1:{running_server.port}/")
    page.wait_for_selector(".layout")

    assert page.is_visible(".brand")
    assert page.is_visible(".nav-tabs")
    assert page.is_visible(".cards-grid")

    page.close()
