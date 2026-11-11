"""Tests for HTTP API routes, Ingress security, and JSON responses."""

import pytest
from app.models import Priority, TargetType


def test_ingress_security_allowed_proxy(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["demo_mode"] is True


def test_security_headers(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert res.headers.get("Referrer-Policy") == "no-referrer"


def test_ingress_forbidden_untrusted_ip(app):
    from conftest import make_test_client
    # IP not in allowed list
    untrusted_client = make_test_client(app, client=("192.168.1.99", 50000))
    res = untrusted_client.get("/api/health")
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")

    # A forged Ingress header MUST NOT bypass the network trust boundary.
    res_ingress = untrusted_client.get("/api/health", headers={"X-Ingress-Path": "/api/hassio_ingress/xyz"})
    assert res_ingress.status_code == 403


def test_summary_and_services(client):
    res_sum = client.get("/api/summary")
    assert res_sum.status_code == 200
    s_data = res_sum.json()
    assert s_data["ha_connected"] is True
    assert s_data["demo_mode"] is True

    res_svc = client.get("/api/services")
    assert res_svc.status_code == 200
    svcs = res_svc.json()["services"]
    assert len(svcs) >= 3


def test_recipients_api(client):
    # Create recipient
    create_res = client.post("/api/recipients", json={
        "name": "Heimdall",
        "timezone": "Europe/Oslo",
        "enabled": True,
    })
    assert create_res.status_code == 200
    rec = create_res.json()["recipient"]
    rec_id = rec["id"]
    assert rec["name"] == "Heimdall"

    # List
    list_res = client.get("/api/recipients")
    assert list_res.status_code == 200
    assert any(r["id"] == rec_id for r in list_res.json()["recipients"])

    # Create Route for recipient
    route_res = client.post("/api/routes", json={
        "recipient_id": rec_id,
        "name": "Bifrost Phone",
        "ha_domain": "notify",
        "ha_service": "mobile_app_bifrost",
        "priority_min": "normal",
        "enabled": True,
    })
    assert route_res.status_code == 200
    rt_id = route_res.json()["route"]["id"]

    # Test route ping
    test_rt_res = client.post(f"/api/routes/{rt_id}/test", json={})
    assert test_rt_res.status_code == 200
    assert test_rt_res.json()["success"] is True

    # Delete route
    del_rt_res = client.delete(f"/api/routes/{rt_id}")
    assert del_rt_res.status_code == 200

    # Delete recipient
    del_rec_res = client.delete(f"/api/recipients/{rec_id}")
    assert del_rec_res.status_code == 200


def test_groups_api(client):
    create_res = client.post("/api/groups", json={
        "name": "Valhalla",
        "description": "Hall of warriors",
        "recipient_ids": [],
    })
    assert create_res.status_code == 200
    gid = create_res.json()["group"]["id"]

    list_res = client.get("/api/groups")
    assert list_res.status_code == 200
    assert any(g["id"] == gid for g in list_res.json()["groups"])

    del_res = client.delete(f"/api/groups/{gid}")
    assert del_res.status_code == 200


def test_policies_api(client):
    create_res = client.post("/api/policies", json={
        "target_id": "household_admin",
        "target_type": "recipient",
        "quiet_start": "22:00",
        "quiet_end": "06:00",
        "day_mask": [0, 1, 2, 3, 4],
        "urgent_override": True,
    })
    assert create_res.status_code == 200
    pid = create_res.json()["policy"]["id"]

    list_res = client.get("/api/policies")
    assert list_res.status_code == 200
    assert any(p["id"] == pid for p in list_res.json()["policies"])

    del_res = client.delete(f"/api/policies/{pid}")
    assert del_res.status_code == 200


def test_preview_and_send_api(client):
    # Preview
    preview_res = client.post("/api/send/preview", json={
        "target_type": "all",
        "priority": "normal",
        "title": "Welcome",
        "message": "Testing Ingress UI",
    })
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert "items" in preview_data

    # Execute send
    send_res = client.post("/api/send", json={
        "target_type": "all",
        "priority": "normal",
        "title": "Hello",
        "message": "Broadcast message",
    })
    assert send_res.status_code == 200
    assert "records" in send_res.json()

    # Check history
    hist_res = client.get("/api/history")
    assert hist_res.status_code == 200
    assert len(hist_res.json()["history"]) > 0

    # Purge history
    purge_res = client.post("/api/history/purge?days=0", json={})
    assert purge_res.status_code == 200
    assert purge_res.json()["status"] == "purged"
