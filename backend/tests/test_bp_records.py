from datetime import datetime, timedelta, timezone


VALID = {"username": "alice", "email": "alice@example.com", "password": "secret123"}
OTHER = {"username": "bob", "email": "bob@example.com", "password": "secret123"}


def _register_and_auth(client, payload=VALID):
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201
    token = r.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _payload(**over):
    base = {
        "systolic": 120,
        "diastolic": 80,
        "heart_rate": 72,
        "measured_at": _iso(datetime.now(timezone.utc)),
        "source": "manual",
    }
    base.update(over)
    return base


class TestAuth:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/bp-records").status_code == 401
        assert client.post("/api/v1/bp-records", json=_payload()).status_code == 401


class TestCrud:
    def test_create_and_get(self, client):
        h = _register_and_auth(client)
        r = client.post("/api/v1/bp-records", json=_payload(), headers=h)
        assert r.status_code == 201
        rec = r.json()
        assert rec["systolic"] == 120 and rec["diastolic"] == 80

        r2 = client.get(f"/api/v1/bp-records/{rec['id']}", headers=h)
        assert r2.status_code == 200 and r2.json()["id"] == rec["id"]

    def test_list_pagination(self, client):
        h = _register_and_auth(client)
        for i in range(5):
            p = _payload(
                systolic=110 + i,
                measured_at=_iso(datetime.now(timezone.utc) - timedelta(hours=i)),
            )
            assert client.post("/api/v1/bp-records", json=p, headers=h).status_code == 201
        r = client.get("/api/v1/bp-records?page=1&size=3", headers=h)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 5 and len(body["items"]) == 3

    def test_update_and_delete(self, client):
        h = _register_and_auth(client)
        rid = client.post("/api/v1/bp-records", json=_payload(), headers=h).json()["id"]
        r = client.patch(
            f"/api/v1/bp-records/{rid}", json={"systolic": 135}, headers=h
        )
        assert r.status_code == 200 and r.json()["systolic"] == 135
        assert client.delete(f"/api/v1/bp-records/{rid}", headers=h).status_code == 204
        assert client.get(f"/api/v1/bp-records/{rid}", headers=h).status_code == 404

    def test_user_isolation(self, client):
        h1 = _register_and_auth(client, VALID)
        h2 = _register_and_auth(client, OTHER)
        rid = client.post("/api/v1/bp-records", json=_payload(), headers=h1).json()["id"]
        assert client.get(f"/api/v1/bp-records/{rid}", headers=h2).status_code == 404
        assert client.get("/api/v1/bp-records", headers=h2).json()["total"] == 0

    def test_validation_out_of_range(self, client):
        h = _register_and_auth(client)
        r = client.post("/api/v1/bp-records", json=_payload(systolic=500), headers=h)
        assert r.status_code == 422


class TestStatsAndForecast:
    def test_stats_empty(self, client):
        h = _register_and_auth(client)
        r = client.get("/api/v1/bp-records/stats?days=7", headers=h)
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 0 and body["window_days"] == 7

    def test_stats_with_data(self, client):
        h = _register_and_auth(client)
        for s, d in [(120, 80), (130, 85), (140, 90)]:
            client.post("/api/v1/bp-records", json=_payload(systolic=s, diastolic=d), headers=h)
        body = client.get("/api/v1/bp-records/stats?days=30", headers=h).json()
        assert body["count"] == 3
        assert body["systolic_max"] == 140 and body["systolic_min"] == 120
        assert abs(body["systolic_avg"] - 130.0) < 0.01

    def test_forecast_insufficient(self, client):
        h = _register_and_auth(client)
        body = client.get("/api/v1/bp-records/forecast", headers=h).json()
        assert body["trend"] == "unknown" and body["points"] == []

    def test_forecast_with_data(self, client):
        h = _register_and_auth(client)
        now = datetime.now(timezone.utc)
        for i, s in enumerate([120, 122, 125, 128, 130]):
            p = _payload(systolic=s, measured_at=_iso(now - timedelta(days=4 - i)))
            client.post("/api/v1/bp-records", json=p, headers=h)
        body = client.get("/api/v1/bp-records/forecast", headers=h).json()
        assert len(body["points"]) >= 1
        assert body["trend"] in ("up", "down", "stable")
