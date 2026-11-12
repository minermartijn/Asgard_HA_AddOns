"""HTTP API and multi-channel notification integration tests for ASGARD RainBreak."""

from pathlib import Path
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


def make_client(tmp_path: Path, require_ingress: bool = False) -> TestClient:
    settings = Settings(
        demo_mode=True,
        default_timezone="Europe/Amsterdam",
        db_path=str(tmp_path / "test_rain_break.db"),
        require_ingress_header=require_ingress,
        pushover_app_token="demo_global_app_token_123",
    )
    app = create_app(settings)
    return TestClient(app)


def test_health_and_overview_defaults(tmp_path: Path):
    with make_client(tmp_path) as client:
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert data["default_timezone"] == "Europe/Amsterdam"

        ov = client.get("/api/overview").json()
        assert len(ov["users"]) == 2
        # Primary user enabled by default, secondary user disabled by default
        assert ov["users"][0]["enabled"] is True
        assert ov["users"][1]["enabled"] is False
        # 3 default workday breaks (10:00, 12:30, 15:00)
        assert len(ov["breaks"]) == 3
        starts = [b["start_time"] for b in ov["breaks"]]
        assert starts == ["10:00", "12:30", "15:00"]
        # Break evaluations computed
        assert len(ov["break_evaluations"]) == 3


def test_per_user_toggle_and_pushover_plus_ha_notify_dispatch(tmp_path: Path):
    with make_client(tmp_path) as client:
        # Configure primary user with both HA Notify AND Pushover
        u_resp = client.get("/api/users").json()["users"][0]
        u_resp["pushover_enabled"] = True
        u_resp["pushover_user_key"] = "uQiRzpo4DXghDmr9QzzfQu27cmVRsG"
        u_resp["ha_notify_enabled"] = True
        u_resp["ha_notify_targets"] = ["notify.mobile_app_mart_s25"]

        save_res = client.post("/api/users", json=u_resp)
        assert save_res.status_code == 200

        # Toggle secondary user on and back off
        t_on = client.post("/api/users/usr_secondary/toggle", json={"enabled": True})
        assert t_on.status_code == 200
        assert t_on.json()["enabled"] is True

        t_off = client.post("/api/users/usr_secondary/toggle", json={"enabled": False})
        assert t_off.status_code == 200
        assert t_off.json()["enabled"] is False

        # Send Urgent test notification to primary user -> should dispatch to both HA Notify and Pushover
        test_res = client.post(
            "/api/test-notification",
            json={"user_id": "usr_primary", "urgency": "urgent"},
        )
        assert test_res.status_code == 200
        body = test_res.json()
        assert body["summary"]["submitted"] == 2
        channels = {r["channel"] for r in body["records"]}
        assert channels == {"ha_notify", "pushover"}
        assert all(r["urgency"] == "urgent" for r in body["records"])


def test_demo_scenarios_and_break_evaluation_dispatch(tmp_path: Path):
    with make_client(tmp_path) as client:
        # Set scenario to workday_break_rain -> 10:00 break has rain, 09:45-10:00 is dry
        scen = client.post("/api/demo/scenario", json={"scenario": "workday_break_rain"})
        assert scen.status_code == 200
        evals = scen.json()["break_evaluations"]
        morning_eval = next(e for e in evals if e["planned_start"] == "10:00")
        assert morning_eval["status"] == "shift_earlier_dry"
        assert morning_eval["recommended_slot"]["start_time"] == "09:45"

        # Trigger manual advice send for morning break
        run_res = client.post(
            "/api/evaluate/run",
            json={
                "break_id": morning_eval["break_id"],
                "send_notifications": True,
                "ignore_dedup": True,
            },
        )
        assert run_res.status_code == 200
        recs = run_res.json()["records"]
        assert len(recs) >= 1
        assert recs[0]["status"] == "submitted"


def test_ingress_header_injection_and_guard(tmp_path: Path):
    with make_client(tmp_path, require_ingress=True) as client:
        # Without X-Ingress-Path -> 403
        r_denied = client.get("/api/health")
        assert r_denied.status_code == 403

        # With X-Ingress-Path -> 200 and dynamic <base> tag injected on index
        headers = {"X-Ingress-Path": "/api/hassio_ingress/rain_token_123"}
        r_ok = client.get("/", headers=headers)
        assert r_ok.status_code == 200
        assert '<base href="/api/hassio_ingress/rain_token_123/" />' in r_ok.text
