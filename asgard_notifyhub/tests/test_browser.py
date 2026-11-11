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
    page.select_option("#comp-priority", "urgent")
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


def test_modal_dropdown_interactions_and_backdrop_close(browser_instance, ingress_server):
    """Verify that clicking dropdowns/select elements in modals never prematurely closes the dialog."""
    page = browser_instance.new_page()
    ingress_url = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}/"
    page.goto(ingress_url)
    page.wait_for_selector(".nav-tabs")

    # Navigate to Recipients & Routes
    page.click('button[data-tab="tab-recipients"]')
    page.wait_for_selector("#btn-add-recipient")

    # Open Add Recipient modal
    page.click("#btn-add-recipient")
    page.wait_for_selector("#modal-rec-form")
    assert page.is_visible("#app-modal")

    # Click on the input inside the modal - modal must stay open
    page.click("#rec-name")
    assert page.is_visible("#app-modal")

    # Close modal via close button
    page.click("#modal-close-btn")
    page.wait_for_function('() => !document.getElementById("app-modal").hasAttribute("open")')

    # If recipients exist, open Add Route modal and click select dropdowns
    cards = page.query_selector_all(".recipient-card")
    if cards:
        route_btn = cards[0].query_selector(".routes-header button")
        if route_btn:
            route_btn.click()
            page.wait_for_selector("#route-service")
            assert page.is_visible("#app-modal")

            # Click the select dropdown - modal must NOT close!
            page.click("#route-service")
            assert page.is_visible("#app-modal")

            page.click("#route-min-priority")
            assert page.is_visible("#app-modal")

            # Click the backdrop directly (e.target === el.appModal)
            page.evaluate("() => document.getElementById('app-modal').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}))")
            page.wait_for_function('() => !document.getElementById("app-modal").hasAttribute("open")')

    page.close()


def test_composer_target_modes_and_visibility(browser_instance, ingress_server):
    """Verify Single Recipient | Group | Everyone target selection, hidden attributes, and confirmation text."""
    page = browser_instance.new_page()
    ingress_url = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}/"
    page.goto(ingress_url)
    page.wait_for_selector(".nav-tabs")

    page.click('button[data-tab="tab-composer"]')
    page.wait_for_selector("#comp-target-modes")

    # Default mode: Single Recipient
    assert page.is_visible("#comp-group-recipient-wrap")
    assert not page.is_visible("#comp-group-select-wrap")
    assert not page.is_visible("#comp-everyone-wrap")
    assert not page.is_disabled("#comp-recipient-id")
    assert page.is_disabled("#comp-group-id")
    summary_text = page.inner_text("#comp-target-summary")
    assert summary_text.startswith("Sending to:") and "route" in summary_text

    # Switch repeatedly across all three modes: Group -> Everyone -> Single Recipient -> Everyone -> Group -> Single Recipient
    for mode in ("group", "all", "recipient", "all", "group", "recipient"):
        page.click(f'.segment-option[data-target-mode="{mode}"]')
        conf = page.inner_text("#comp-target-summary")
        assert conf.startswith("Sending to:")
        if mode == "recipient":
            assert page.is_visible("#comp-group-recipient-wrap")
            assert not page.is_visible("#comp-group-select-wrap")
            assert not page.is_visible("#comp-everyone-wrap")
            assert not page.is_disabled("#comp-recipient-id")
            assert page.is_disabled("#comp-group-id")
            assert "route" in conf
        elif mode == "group":
            assert not page.is_visible("#comp-group-recipient-wrap")
            assert page.is_visible("#comp-group-select-wrap")
            assert not page.is_visible("#comp-everyone-wrap")
            assert page.is_disabled("#comp-recipient-id")
            assert not page.is_disabled("#comp-group-id")
            assert "recipient" in conf
        else:
            assert not page.is_visible("#comp-group-recipient-wrap")
            assert not page.is_visible("#comp-group-select-wrap")
            assert page.is_visible("#comp-everyone-wrap")
            assert page.is_disabled("#comp-recipient-id")
            assert page.is_disabled("#comp-group-id")
            assert "Everyone" in conf and "enabled" in conf

    page.close()


def test_dispatch_outcome_banners_honest_reporting(browser_instance, ingress_server):
    """Verify honest banner and preview reporting for submitted, suppressed, priority-blocked, and mixed outcomes."""
    from app.models import Priority, QuietPolicy, Recipient, Route, TargetType

    storage = ingress_server.storage
    client = ingress_server.client

    # Set up dedicated recipients for each scenario
    storage.save_recipient(Recipient(id="rec_quiet_ui", name="Freya Quiet", timezone="Europe/Amsterdam", enabled=True))
    storage.save_route(
        Route(id="rt_quiet_ui", recipient_id="rec_quiet_ui", name="Freya Phone", ha_domain="notify", ha_service="mobile_app_pixel")
    )
    storage.save_policy(
        QuietPolicy(
            id="pol_quiet_ui",
            target_id="rec_quiet_ui",
            target_type=TargetType.RECIPIENT,
            quiet_start="00:00",
            quiet_end="23:59",
            day_mask=[0, 1, 2, 3, 4, 5, 6],
            timezone="UTC",
            urgent_override=False,
            enabled=True,
        )
    )

    storage.save_recipient(Recipient(id="rec_mix_ui", name="Thor Mixed", timezone="Europe/Amsterdam", enabled=True))
    storage.save_route(
        Route(id="rt_mix_ok", recipient_id="rec_mix_ui", name="Thor Mobile App", ha_domain="notify", ha_service="mobile_app_pixel")
    )
    storage.save_route(
        Route(id="rt_mix_fail", recipient_id="rec_mix_ui", name="Galaxy Watch Entity", ha_domain="notify", ha_service="galaxy_watch5_fhyw")
    )
    client.fail_actions["notify.galaxy_watch5_fhyw"] = (
        "The integration behind notification entity notify.galaxy_watch5_fhyw raised an error while sending (HTTP 500)."
    )

    storage.save_recipient(Recipient(id="rec_prio_ui", name="Heimdall Priority", timezone="Europe/Amsterdam", enabled=True))
    storage.save_route(
        Route(
            id="rt_prio_urgent",
            recipient_id="rec_prio_ui",
            name="Urgent Horn",
            ha_domain="notify",
            ha_service="mobile_app_pixel",
            priority_min=Priority.URGENT,
            enabled=True,
        )
    )
    storage.save_route(
        Route(
            id="rt_prio_disabled",
            recipient_id="rec_prio_ui",
            name="Disabled Horn",
            ha_domain="notify",
            ha_service="notify",
            priority_min=Priority.INFORMATIONAL,
            enabled=False,
        )
    )

    page = browser_instance.new_page()
    ingress_url = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}/"
    page.goto(ingress_url)
    page.wait_for_selector(".nav-tabs")
    page.click('button[data-tab="tab-composer"]')
    page.wait_for_selector("#comp-recipient-id")

    # 1. Suppressed by quiet hours -> warning banner, NOT labeled as Dispatched
    page.select_option("#comp-recipient-id", "rec_quiet_ui")
    page.select_option("#comp-priority", "normal")
    page.fill("#comp-message", "Night message that should be silenced.")
    page.click("#btn-execute-send")
    page.wait_for_selector("#status-banner.banner-warning")
    banner_txt = page.inner_text("#status-banner")
    assert "0 submitted" in banner_txt
    assert "silenced by quiet hours" in banner_txt
    assert not banner_txt.startswith("Dispatched:")
    assert "silenced · quiet hours" in page.inner_text("#preview-results-container").lower()

    # 2. Priority blocked + Disabled route -> distinct statuses in preview and dispatch
    page.select_option("#comp-recipient-id", "rec_prio_ui")
    page.select_option("#comp-priority", "informational")
    page.fill("#comp-message", "Low priority check.")
    page.click("#btn-execute-send")
    page.wait_for_function(
        '() => document.getElementById("status-banner").innerText.includes("blocked by minimum priority")'
    )
    prio_banner = page.inner_text("#status-banner")
    assert "blocked by minimum priority" in prio_banner
    assert "skipped (route disabled)" in prio_banner
    preview_txt = page.inner_text("#preview-results-container").lower()
    assert "blocked · min priority" in preview_txt
    assert "skipped · route disabled" in preview_txt

    # 3. Mixed results (1 submitted, 1 failed Galaxy Watch HTTP 500) -> warning banner with breakdown
    page.select_option("#comp-recipient-id", "rec_mix_ui")
    page.select_option("#comp-priority", "urgent")
    page.fill("#comp-message", "Mixed route test.")
    page.click("#btn-execute-send")
    page.wait_for_function(
        '() => document.getElementById("status-banner").innerText.includes("1 of 2 submitted to Home Assistant")'
    )
    mix_banner = page.inner_text("#status-banner")
    assert "1 of 2 submitted to Home Assistant" in mix_banner
    assert "1 failed Home Assistant action" in mix_banner
    mix_preview = page.inner_text("#preview-results-container").lower()
    assert "submitted to ha" in mix_preview
    assert "failed · ha rejected" in mix_preview
    assert "http 500" in mix_preview

    page.close()


def test_orphaned_policy_detection_and_policy_editing(browser_instance, ingress_server):
    """Verify orphaned policies are clearly labeled and can be reassigned via Edit."""
    from app.models import QuietPolicy, TargetType

    storage = ingress_server.storage
    storage.save_policy(
        QuietPolicy(
            id="pol_orphan_browser",
            target_id="rec_nonexistent_99",
            target_type=TargetType.RECIPIENT,
            quiet_start="21:30",
            quiet_end="06:30",
            timezone="UTC",
            enabled=True,
        )
    )

    page = browser_instance.new_page()
    ingress_url = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}/"
    page.goto(ingress_url)
    page.wait_for_selector(".nav-tabs")

    page.click('button[data-tab="tab-policies"]')
    page.wait_for_selector('[data-policy-id="pol_orphan_browser"]')
    card_text = page.inner_text('[data-policy-id="pol_orphan_browser"]')
    assert "Orphaned Policy · Deleted Recipient" in card_text
    assert "orphaned target" in card_text.lower()

    # Edit the orphaned policy to reassign it to an active recipient and Europe/Amsterdam
    page.click('[data-policy-id="pol_orphan_browser"] button:has-text("Edit")')
    page.wait_for_selector("#modal-policy-form")
    page.fill("#pol-tz", "Europe/Amsterdam")
    page.fill("#pol-start", "23:00")
    page.click('#modal-policy-form button[type="submit"]')
    page.wait_for_selector("#status-banner.banner-success")

    updated_text = page.inner_text('[data-policy-id="pol_orphan_browser"]')
    assert "orphaned target" not in updated_text.lower()
    assert "Europe/Amsterdam" in updated_text
    assert "23:00" in updated_text

    page.close()


@pytest.mark.parametrize(
    "viewport",
    [
        {"width": 320, "height": 568},
        {"width": 360, "height": 640},
        {"width": 375, "height": 667},
        {"width": 390, "height": 844},
        {"width": 412, "height": 915},
        {"width": 430, "height": 932},
        {"width": 568, "height": 320},  # Landscape mobile
        {"width": 768, "height": 1024},  # Tablet
        {"width": 1024, "height": 768},  # Desktop
    ],
)
def test_responsive_viewports_no_horizontal_overflow_and_mobile_audit_cards(
    browser_instance, ingress_server, viewport
):
    """Verify zero page-level horizontal overflow across all 6 tabs and modals from 320px to 1024px."""
    page = browser_instance.new_page()
    page.set_viewport_size(viewport)
    ingress_url = f"http://127.0.0.1:{ingress_server.port}{ingress_server.ingress_prefix}/"
    page.goto(ingress_url)
    page.wait_for_selector(".layout")

    tab_ids = [
        "tab-dashboard",
        "tab-composer",
        "tab-recipients",
        "tab-groups",
        "tab-policies",
        "tab-history",
    ]

    for tid in tab_ids:
        btn_selector = f'button[data-tab="{tid}"]'
        assert page.is_visible(btn_selector), f"Tab button {tid} not visible at {viewport}"
        page.click(btn_selector)
        page.wait_for_selector(f"#{tid}")
        assert page.is_visible(f"#{tid}")
        assert page.get_attribute(btn_selector, "aria-selected") == "true"

        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 1, f"Horizontal overflow ({overflow}px) on {tid} at viewport {viewport}"

    # Verify Audit History responsive presentation
    if viewport["width"] <= 720:
        assert page.is_visible("#history-cards")
        assert not page.is_visible("#history-table-wrap")
    else:
        assert page.is_visible("#history-table-wrap")

    # Also verify modal fits within viewport without horizontal overflow
    page.click('button[data-tab="tab-recipients"]')
    page.click("#btn-add-recipient")
    page.wait_for_selector("#modal-rec-form")
    modal_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert modal_overflow <= 1, f"Modal caused horizontal overflow at {viewport}"
    page.click("#modal-close-btn")

    page.close()
