"""Playwright end-to-end browser tests for ASGARD RainBreak under simulated Home Assistant Ingress."""

import os
from pathlib import Path
import socket
import threading
import time
from typing import Optional
from fastapi import FastAPI, Response
from playwright.sync_api import sync_playwright
import pytest
import uvicorn

from app.main import create_app
from app.settings import Settings


def get_browser_executable() -> Optional[str]:
    env_bin = os.environ.get("PLAYWRIGHT_CHROME_BIN")
    if env_bin and os.path.exists(env_bin):
        return env_bin
    for candidate in ("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(candidate):
            return candidate
    return None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class IngressTestServer:
    def __init__(self, tmp_path: Path):
        self.port = _free_port()
        self.ingress_prefix = "/api/hassio_ingress/rain_break_session_42"

        settings = Settings(
            demo_mode=True,
            default_timezone="Europe/Amsterdam",
            db_path=str(tmp_path / "browser_rain_break.db"),
            pushover_app_token="demo_app_token_browser",
        )
        self.inner_app = create_app(settings)
        self.outer_app = FastAPI()
        self.outer_app.mount(self.ingress_prefix, self.inner_app)

        @self.outer_app.get("/favicon.ico")
        async def root_favicon():
            return Response(status_code=204)

        self.config = uvicorn.Config(self.outer_app, host="127.0.0.1", port=self.port, log_level="error")
        self.server = uvicorn.Server(self.config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self):
        self.thread.start()
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("IngressTestServer did not start in time")

    def stop(self):
        self.server.should_exit = True
        self.thread.join(timeout=5)


@pytest.fixture(scope="module")
def browser_instance():
    exe = get_browser_executable()
    with sync_playwright() as p:
        if exe:
            browser = p.chromium.launch(executable_path=exe, headless=True)
        else:
            browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="module")
def ingress_server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rain_break_ingress")
    srv = IngressTestServer(tmp)
    srv.start()
    yield srv
    srv.stop()


def test_ingress_dashboard_break_advisor_and_user_modal(browser_instance, ingress_server):
    page = browser_instance.new_page()
    escaped_requests = []

    def on_request(req):
        if f"127.0.0.1:{ingress_server.port}" in req.url and "favicon.ico" not in req.url:
            if ingress_server.ingress_prefix not in req.url:
                escaped_requests.append(req.url)

    page.on("request", on_request)

    url = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}/"
    page.goto(url)
    page.wait_for_selector(".eval-card")

    # Verify the 10:00 break evaluation recommends 09:45-10:00 (15 min earlier)
    dash_text = page.inner_text("#dashboard-break-evaluations")
    assert "Morning Break Walk (10:00)" in dash_text
    assert "09:45" in dash_text
    assert "15 min earlier" in dash_text

    # Switch to Users & Channels tab and open Configure modal
    page.click('button[data-tab="tab-users"]')
    page.wait_for_selector("#users-list .item-card")
    users_text = page.inner_text("#users-list")
    assert "Martijn" in users_text

    # Open Add User modal and verify native <select> interaction does not close modal
    page.click("#btn-add-user")
    page.wait_for_selector("#modal-user-form")
    page.select_option("#usr-loc-mode", "fixed_location")
    page.select_option("#usr-sched-mode", "urgent_window_else_neutral")
    assert page.is_visible("#modal-user-form")

    page.fill("#usr-name", "Test Cyclist")
    page.check("#usr-po-enabled")
    page.fill("#usr-po-user", "uTestPushoverUserKey999")
    page.click('#modal-user-form button[type="submit"]')
    page.wait_for_function('() => document.getElementById("users-list").innerText.includes("Test Cyclist")')

    assert escaped_requests == []
    page.close()


@pytest.mark.parametrize(
    "viewport",
    [
        {"width": 320, "height": 568},
        {"width": 375, "height": 667},
        {"width": 768, "height": 1024},
        {"width": 1024, "height": 768},
    ],
)
def test_responsive_viewports_no_horizontal_overflow(browser_instance, ingress_server, viewport):
    page = browser_instance.new_page()
    page.set_viewport_size(viewport)
    url = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}/"
    page.goto(url)
    page.wait_for_selector(".eval-card")

    for tid in ("tab-dashboard", "tab-breaks", "tab-users", "tab-locations", "tab-settings"):
        page.click(f'button[data-tab="{tid}"]')
        page.wait_for_selector(f"#{tid}")
        overflow = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1, f"Horizontal overflow ({overflow}px) on {tid} at {viewport}"

    page.close()
