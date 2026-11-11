"""HTTP API, Ingress, caching and security tests (mock sources only)."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import ApiStatus
from app.normalize import ParseResult
from app.settings import Settings, load_settings
from app.sources import DemoBackupSource, MockBackupSource, SourceError

FIXTURES = Path(__file__).parent / "fixtures"
SUPERVISOR_PROXY = ("172.30.32.2", 40000)


@dataclass
class ScriptedSource:
    """Returns queued results/errors in order; counts calls."""

    script: list
    demo: bool = False
    calls: int = field(default=0)

    async def fetch(self) -> ParseResult:
        self.calls += 1
        item = self.script[min(self.calls - 1, len(self.script) - 1)]
        if isinstance(item, Exception):
            raise item
        return await item.fetch()


def client_for(source, **overrides):
    settings = Settings(**{"min_refresh_interval_seconds": 0.0, **overrides})
    return TestClient(create_app(settings=settings, source=source), client=SUPERVISOR_PROXY)


def mock(name):
    return MockBackupSource(fixture_path=FIXTURES / name, demo=False)


# ---- routes ----------------------------------------------------------------

def test_health_is_minimal():
    c = client_for(mock("backups_ok.json"))
    r = c.get("/api/health")
    assert r.status_code == 200
    assert set(r.json()) == {"status", "version"}


def test_summary_and_backups_ok():
    c = client_for(mock("backups_ok.json"), stale_threshold_hours=24 * 365 * 10)
    s = c.get("/api/summary").json()
    assert s["api_status"] == "ok"
    assert s["freshness"] == "fresh"
    assert s["total_count"] == 3
    assert s["unknown_size_count"] == 1
    assert s["known_size_total_bytes"] == 1288490189 + 178257
    assert s["supervisor_days_until_stale"] == 3
    assert s["demo_mode"] is False

    b = c.get("/api/backups").json()
    assert b["total"] == 3
    ids = [i["id"] for i in b["items"]]
    assert ids == ["fake0001", "fake0002", "fake0003"]  # newest first
    assert b["items"][2]["size_bytes"] is None


def test_backups_pagination_and_bounds():
    c = client_for(mock("backups_ok.json"))
    page = c.get("/api/backups?offset=1&limit=1").json()
    assert [i["id"] for i in page["items"]] == ["fake0002"]
    assert c.get("/api/backups?limit=0").status_code == 422
    assert c.get("/api/backups?limit=10000").status_code == 422
    assert c.get("/api/backups?offset=-1").status_code == 422


def test_empty_says_no_backups():
    s = client_for(mock("backups_empty.json")).get("/api/summary").json()
    assert s["freshness"] == "no_backups"
    assert s["total_count"] == 0


def test_forbidden_is_explained_without_crash():
    src = ScriptedSource([SourceError(ApiStatus.FORBIDDEN, "not allowed (403)")])
    r = client_for(src).get("/api/summary")
    assert r.status_code == 200
    s = r.json()
    assert s["api_status"] == "forbidden"
    assert s["freshness"] == "unknown"
    assert "403" in s["error_message"]


def test_timeout_after_success_keeps_cached_data_marked_stale():
    src = ScriptedSource([mock("backups_ok.json"), SourceError(ApiStatus.UNAVAILABLE, "timeout")])
    c = client_for(src)
    first = c.get("/api/summary").json()
    assert first["api_status"] == "ok"
    r = c.post("/api/refresh")
    assert r.status_code == 200
    s = c.get("/api/summary").json()
    assert s["api_status"] == "unavailable"
    assert s["showing_cached_data"] is True
    assert s["total_count"] == 3
    assert s["last_success_utc"] == first["last_success_utc"]
    assert c.get("/api/backups").json()["total"] == 3


def test_summary_is_cached_between_requests():
    src = ScriptedSource([mock("backups_ok.json")])
    c = client_for(src)
    for _ in range(5):
        c.get("/api/summary")
        c.get("/api/backups")
    assert src.calls == 1


def test_refresh_rate_limited():
    src = ScriptedSource([mock("backups_ok.json")])
    c = client_for(src, min_refresh_interval_seconds=60.0)
    c.get("/api/summary")
    r = c.post("/api/refresh")
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 1
    assert src.calls == 1


def test_demo_mode_is_labelled():
    s = client_for(DemoBackupSource()).get("/api/summary").json()
    assert s["demo_mode"] is True
    assert s["freshness"] == "fresh"
    assert s["unknown_size_count"] == 1


# ---- Ingress / frontend ------------------------------------------------------

def test_index_and_assets_use_relative_urls_only():
    c = client_for(mock("backups_ok.json"))
    html = c.get("/").text
    refs = re.findall(r'(?:href|src)="([^"]+)"', html)
    assert refs, "expected asset references"
    for ref in refs:
        assert not ref.startswith("/"), f"absolute path breaks Ingress: {ref}"
        assert "://" not in ref, f"external asset/CDN not allowed: {ref}"
    js = c.get("/static/app.js").text
    fetches = re.findall(r"getJSON\('([^']+)'", js)
    assert fetches and all(not f.startswith("/") for f in fetches)
    assert c.get("/static/app.css").status_code == 200


def test_works_with_ingress_style_headers():
    c = client_for(mock("backups_ok.json"))
    headers = {"X-Ingress-Path": "/api/hassio_ingress/RANDOMtoken123"}
    assert c.get("/", headers=headers).status_code == 200
    assert c.get("/api/summary", headers=headers).status_code == 200


# ---- security ----------------------------------------------------------------

def test_requests_not_from_supervisor_proxy_are_refused():
    app = create_app(settings=Settings(), source=mock("backups_ok.json"))
    other = TestClient(app, client=("172.30.33.5", 1234))
    for path in ("/", "/api/summary", "/api/backups", "/api/health", "/static/app.js"):
        assert other.get(path).status_code == 403
    assert other.post("/api/refresh").status_code == 403


@pytest.mark.parametrize(
    "method, path",
    [
        ("POST", "/api/backups"),
        ("DELETE", "/api/backups"),
        ("GET", "/api/backups/fake0001/download"),
        ("POST", "/api/backups/fake0001/restore"),
        ("DELETE", "/api/backups/fake0001"),
        ("POST", "/api/backups/new/full"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
    ],
)
def test_no_destructive_or_introspection_routes(method, path):
    c = client_for(mock("backups_ok.json"))
    assert c.request(method, path).status_code in (404, 405)


def test_route_table_is_read_only():
    app = create_app(settings=Settings(), source=mock("backups_ok.json"))
    mutating = {
        (route.path, method)
        for route in app.routes
        for method in getattr(route, "methods", set()) or set()
        if method not in {"GET", "HEAD"}
    }
    assert mutating == {("/api/refresh", "POST")}


def test_security_headers_present():
    r = client_for(mock("backups_ok.json")).get("/")
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_settings_defaults_and_clamping(tmp_path, monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    monkeypatch.delenv("ASGARD_ALLOWED_CLIENTS", raising=False)
    s = load_settings(tmp_path / "missing.json")
    assert s.stale_threshold_hours == 48 and s.demo_mode is False
    assert s.allowed_clients == ("172.30.32.2",)

    opts = tmp_path / "options.json"
    opts.write_text('{"stale_threshold_hours": 999999, "demo_mode": "yes"}')
    s = load_settings(opts)
    assert s.stale_threshold_hours == 2160
    assert s.demo_mode is False  # only a real boolean enables demo mode

    opts.write_text("{not json")
    assert load_settings(opts).stale_threshold_hours == 48


def test_build_source():
    from app.main import build_source
    from app.sources import DemoBackupSource, SupervisorBackupSource

    assert isinstance(build_source(Settings(demo_mode=True)), DemoBackupSource)
    sup = build_source(Settings(demo_mode=False, supervisor_token="abc"))
    assert isinstance(sup, SupervisorBackupSource)
    assert sup.token == "abc"


def test_mock_source_missing_file(tmp_path):
    import asyncio

    missing_src = MockBackupSource(fixture_path=tmp_path / "absent.json")
    with pytest.raises(SourceError) as exc:
        asyncio.run(missing_src.fetch())
    assert exc.value.status == ApiStatus.UNAVAILABLE


def test_api_history_endpoint(tmp_path):
    settings = Settings(data_dir=str(tmp_path), min_refresh_interval_seconds=0.0)
    c = TestClient(create_app(settings=settings, source=mock("backups_ok.json")), client=SUPERVISOR_PROXY)
    # Ensure fresh triggers snapshot recording
    r = c.get("/api/summary")
    assert r.status_code == 200

    h = c.get("/api/history")
    assert h.status_code == 200
    entries = h.json().get("entries")
    assert isinstance(entries, list)
    assert len(entries) >= 1
    assert entries[0]["total_count"] == 3


def test_favicon_route():
    c = client_for(mock("backups_ok.json"))
    res = c.get("/favicon.ico")
    assert res.status_code in (200, 204)
