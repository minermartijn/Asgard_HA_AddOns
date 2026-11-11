"""End-to-end browser automation tests for ASGARD NotifyHub under Home Assistant Ingress."""

import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import pytest
import uvicorn
from fastapi import FastAPI
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


class IngressAppServer:
    """Simulates Home Assistant Core with Ingress reverse proxy mount at /api/hassio_ingress/<session>/."""

    def __init__(self, tmp_path: Path):
        self.port = get_free_port()
        self.session_id = "test-session-token-99"
        self.ingress_prefix = f"/api/hassio_ingress/{self.session_id}"

        db_path = tmp_path / "notifyhub_ingress_browser.db"
        self.storage = Storage(db_path)
        self.client = DemoHomeAssistantClient()
        self.service = NotifyHubService(storage=self.storage, ha_client=self.client, demo_mode=True)
        self.settings = Settings(
            db_path=db_path,
            allowed_source_ips="*",
            demo_mode=True,
            default_timezone="UTC",
            dedup_window_seconds=60,
        )
        self.inner_app = create_app(settings=self.settings, service=self.service)

        # Outer app simulating HA Core with Ingress mount
        self.outer_app = FastAPI()
        self.outer_app.mount(self.ingress_prefix, self.inner_app)

        @self.outer_app.get("/favicon.ico")
        async def root_favicon():
            from fastapi import Response
            return Response(status_code=204)

        self.server = uvicorn.Server(
            uvicorn.Config(self.outer_app, host="127.0.0.1", port=self.port, log_level="error")
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        time.sleep(0.5)

    def close(self):
        self.server.should_exit = True
        self.thread.join(timeout=2.0)


@pytest.fixture(scope="module")
def ingress_server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ingress_srv")
    srv = IngressAppServer(tmp)
    yield srv
    srv.close()


def test_ingress_prefix_isolation_and_no_escaped_requests(browser_instance, ingress_server):
    """Verifies that all API requests remain within the Ingress session prefix."""
    page = browser_instance.new_page()
    console_errors = []
    escaped_requests = []

    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" and "favicon" not in msg.text else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    def on_request(request):
        url = request.url
        expected_base = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}"
        if not url.startswith(expected_base) and not url.endswith("/favicon.ico"):
            escaped_requests.append(url)

    page.on("request", on_request)

    # Load via simulated Ingress URL with trailing slash
    ingress_url = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}/"
    page.goto(ingress_url)
    page.wait_for_selector("#stat-ha-conn")

    assert "ASGARD NotifyHub" in page.title()
    assert page.is_visible("#tab-dashboard")
    assert page.inner_text("#stat-ha-conn") in ("Demo Mode", "Connected")

    # Discovered services rendered
    page.wait_for_selector(".service-chip")
    chips = page.query_selector_all(".service-chip")
    assert len(chips) >= 3

    # Assert 0 console errors and 0 escaped requests
    assert len(console_errors) == 0, f"Console errors: {console_errors}"
    assert len(escaped_requests) == 0, f"Requests escaped Ingress prefix: {escaped_requests}"

    page.close()


def test_ingress_full_lifecycle_and_crud(browser_instance, ingress_server):
    """Full lifecycle testing under Ingress: recipients, routes, groups, policies, simulation, history."""
    page = browser_instance.new_page()
    escaped_requests = []

    def on_request(request):
        url = request.url
        expected_base = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}"
        if not url.startswith(expected_base):
            escaped_requests.append(url)

    page.on("request", on_request)

    ingress_url = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}/"
    page.goto(ingress_url)
    page.wait_for_selector(".nav-tabs")

    # 1. Sync Services
    page.click("#btn-refresh-services")
    page.wait_for_selector(".banner-success")

    # 2. Add Recipient
    page.click('button[data-tab="tab-recipients"]')
    page.wait_for_selector("#btn-add-recipient")
    page.click("#btn-add-recipient")
    page.wait_for_selector("#rec-name")
    page.fill("#rec-name", "Odin Allfather")
    page.fill("#rec-tz", "Europe/Amsterdam")
    page.click('#modal-rec-form button[type="submit"]')
    page.wait_for_function('() => document.body.innerText.includes("Odin Allfather")')
    assert "Odin Allfather" in page.content()

    # 3. Add Route to Recipient
    page.click('.recipient-card .routes-header button')
    page.wait_for_selector("#route-name")
    page.fill("#route-name", "Raven Dispatch")
    page.select_option("#route-min-priority", "normal")
    page.click('#modal-route-form button[type="submit"]')
    page.wait_for_function('() => document.body.innerText.includes("Raven Dispatch")')
    assert "Raven Dispatch" in page.content()

    # 4. Test Route Ping
    page.click('.route-actions button:has-text("Ping Test")')
    page.wait_for_selector(".banner-success")

    # 5. Add Group
    page.click('button[data-tab="tab-groups"]')
    page.wait_for_selector("#btn-add-group")
    page.click("#btn-add-group")
    page.wait_for_selector("#grp-name")
    page.fill("#grp-name", "Aesir Guardians")
    page.fill("#grp-desc", "Defenders of the realm")
    page.click('#modal-grp-form button[type="submit"]')
    page.wait_for_function('() => document.body.innerText.includes("Aesir Guardians")')
    assert "Aesir Guardians" in page.content()

    # 6. Add Quiet Hours Policy
    page.click('button[data-tab="tab-policies"]')
    page.wait_for_selector("#btn-add-policy")
    page.click("#btn-add-policy")
    page.wait_for_selector("#pol-start")
    page.fill("#pol-start", "22:00")
    page.fill("#pol-end", "07:00")
    page.click('#modal-policy-form button[type="submit"]')
    page.wait_for_function('() => document.body.innerText.includes("22:00")')

    # 7. Composer Simulation (Dry-Run Preview)
    page.click('button[data-tab="tab-composer"]')
    page.wait_for_selector("#comp-message")
    page.fill("#comp-title", "Frost Giant Incursion")
    page.fill("#comp-message", "Perimeter breach detected in sector 4.")
    page.click("#btn-preview-send")
    page.wait_for_selector(".preview-item")
    items = page.query_selector_all(".preview-item")
    assert len(items) >= 1

    # 8. Dispatch Execution
    page.click("#btn-execute-send")
    page.wait_for_selector(".banner-success")

    # 9. Audit History
    page.click('button[data-tab="tab-history"]')
    page.wait_for_selector("#history-tbody tr")
    rows = page.query_selector_all("#history-tbody tr")
    assert len(rows) >= 1

    # 10. Purge Audit History
    # Handle confirmation dialog
    page.on("dialog", lambda dialog: dialog.accept())
    page.click("#btn-purge-history")
    page.wait_for_selector(".banner-success")

    # Assert ZERO escaped requests throughout entire test flow!
    assert len(escaped_requests) == 0, f"Escaped requests: {escaped_requests}"

    page.close()


def test_mobile_viewport_under_ingress(browser_instance, ingress_server):
    page = browser_instance.new_page()
    page.set_viewport_size({"width": 375, "height": 667})
    ingress_url = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}/"
    page.goto(ingress_url)
    page.wait_for_selector(".layout")

    assert page.is_visible(".brand")
    assert page.is_visible(".nav-tabs")
    assert page.is_visible(".cards-grid")

    page.close()


def test_ingress_without_trailing_slash_loads_and_resolves(browser_instance, ingress_server):
    """Verifies that navigating without trailing slash properly resolves assets and APIs."""
    page = browser_instance.new_page()
    console_errors = []
    escaped_requests = []

    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" and "favicon" not in msg.text else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    def on_request(request):
        url = request.url
        expected_base = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}"
        if not url.startswith(expected_base) and not url.endswith("/favicon.ico"):
            escaped_requests.append(url)

    page.on("request", on_request)

    # Ingress URL WITHOUT trailing slash
    ingress_url_no_slash = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}"
    page.goto(ingress_url_no_slash)
    page.wait_for_selector("#stat-ha-conn")

    assert page.is_visible("#tab-dashboard")
    assert page.inner_text("#stat-ha-conn") in ("Demo Mode", "Connected")

    # Assert 0 console errors and 0 escaped requests
    assert len(console_errors) == 0, f"Console errors: {console_errors}"
    assert len(escaped_requests) == 0, f"Requests escaped Ingress prefix: {escaped_requests}"

    page.close()
