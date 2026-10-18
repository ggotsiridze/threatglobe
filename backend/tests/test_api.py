import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import make_settings

SECRET = "super-secret-test-password"


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_status_reports_demo_without_secrets(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "demo" and body["public_mode"] is True
    assert body["events_stored"] >= 3000  # ~1h at 1.2 events/s
    assert SECRET not in r.text and "es.internal" not in r.text
    assert {"rule", "points"} <= set(body["risk_rules"][0])


def test_stats_shape(client):
    s = client.get("/api/stats").json()
    for key in ("events_today", "unique_source_ips", "countries_observed", "most_targeted_service",
                "top_countries", "top_ports", "top_honeypots", "severity_counts"):  # fmt: skip
        assert key in s
    assert s["events_today"] > 0 and s["most_targeted_service"] == "SSH"


def test_events_listing_is_masked_in_public_mode(client):
    r = client.get("/api/events", params={"limit": 200})
    events = r.json()["events"]
    assert len(events) == 200
    for e in events:
        assert e["source_ip"] is None or e["source_ip"].endswith(".*.*")
        assert e["destination_ip"] is None and e["raw"] is None
        assert e["password"] is None or e["password"][1:] == "••••••"


def test_events_order_and_filters(client):
    asc = client.get("/api/events", params={"limit": 50, "order": "asc"}).json()["events"]
    assert [e["timestamp"] for e in asc] == sorted(e["timestamp"] for e in asc)
    cn = client.get("/api/events", params={"country": "CN", "limit": 20}).json()["events"]
    assert cn and all(e["source_country_code"] == "CN" for e in cn)
    ssh = client.get("/api/events", params={"port": 22, "limit": 20}).json()["events"]
    assert all(e["destination_port"] == 22 for e in ssh)


def test_event_detail_and_404(client):
    first = client.get("/api/events", params={"limit": 1}).json()["events"][0]
    detail = client.get(f"/api/events/{first['id']}").json()
    assert detail == first
    assert client.get("/api/events/does-not-exist").status_code == 404


def test_replay_sized_request_is_accepted(client):
    # The frontend replay loads up to 5000 events in one request.
    r = client.get("/api/events", params={"limit": 5000, "order": "asc"})
    assert r.status_code == 200 and r.json()["count"] > 1000


@pytest.mark.parametrize(
    "path",
    [
        "/api/events?limit=0",
        "/api/events?limit=5001",
        "/api/events?severity=EXTREME",
        "/api/stats?hours=0",
        "/api/events?port=70000",
    ],
)
def test_validation_errors(client, path):
    assert client.get(path).status_code == 422


@pytest.mark.parametrize("path", ["/api/countries", "/api/ports", "/api/honeypots"])
def test_top_lists(client, path):
    items = client.get(path, params={"limit": 5}).json()["items"]
    assert 0 < len(items) <= 5
    counts = [i["count"] for i in items]
    assert counts == sorted(counts, reverse=True)


def test_timeline(client):
    tl = client.get("/api/timeline", params={"hours": 24, "bucket_minutes": 60}).json()
    assert tl["bucket_minutes"] == 60 and len(tl["buckets"]) == 24
    # Test settings load DEMO_HISTORY_HOURS=1, so only the newest buckets have data.
    assert sum(b["total"] for b in tl["buckets"][-2:]) > 0
    assert sum(b["total"] for b in tl["buckets"][:-3]) == 0


def test_private_mode_exposes_full_ip(private_client):
    e = private_client.get("/api/events", params={"limit": 1}).json()["events"][0]
    assert not e["source_ip"].endswith("*")


def test_no_secret_in_any_response(client):
    for path in ["/api/status", "/api/stats", "/api/events?limit=500", "/api/timeline", "/openapi.json"]:
        assert SECRET not in client.get(path).text


def test_websocket_hello_then_streamed_attacks():
    settings = make_settings(DEMO_STREAM_ENABLED=True, DEMO_EVENTS_PER_SECOND=200, DEMO_HISTORY_HOURS=0.05)
    with TestClient(create_app(settings)) as c, c.websocket_connect("/ws/attacks") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["data"]["mode"] == "demo"
        assert len(hello["data"]["recent"]) == 40
        assert hello["data"]["snapshot"]["stats"]["events_today"] > 0
        assert hello["data"]["snapshot"]["timeline"]["bucket_minutes"] == 10
        ws.send_text("ping")
        seen = set()
        attacks = []
        for _ in range(200):
            msg = ws.receive_json()
            seen.add(msg["type"])
            if msg["type"] == "attack":
                attacks.append(msg["data"])
            if {"attack", "pong", "snapshot"} <= seen and len(attacks) >= 5:
                break
        assert {"attack", "pong", "snapshot"} <= seen
        assert all(a["source_ip"] is None or a["source_ip"].endswith(".*.*") for a in attacks)
        stamps = [a["timestamp"] for a in attacks]
        assert stamps == sorted(stamps)


def test_tpot_source_not_yet_available():
    app = create_app(make_settings(THREATGLOBE_SOURCE="tpot"))
    with pytest.raises(RuntimeError, match="REQUIRES REAL T-POT"), TestClient(app):
        pass
