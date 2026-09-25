"""Ten AI-assisted additional BP scenarios, separate from module-one cases."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services import bp_record_service


BASE = "/api/v1/bp-records"
NOW = datetime(2026, 9, 14, 12, tzinfo=timezone.utc)


def auth(client, name="module2_bp"):
    response = client.post("/api/v1/auth/register", json={
        "username": name, "email": name + "@example.com", "password": "secret123",
    })
    assert response.status_code == 201, response.text
    return {"Authorization": "Bearer " + response.json()["tokens"]["access_token"]}


def payload(**changes):
    data = {"systolic": 120, "diastolic": 80, "heart_rate": 72,
            "measured_at": NOW.isoformat(), "source": "manual"}
    data.update(changes)
    return data


def create(client, headers, **changes):
    response = client.post(BASE, headers=headers, json=payload(**changes))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def frozen_clock(monkeypatch):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)

    # Freeze only the service clock; JWT expiry must still use real time.
    monkeypatch.setattr(bp_record_service, "datetime", FrozenDateTime)


@pytest.mark.parametrize("case", ["M2-TC-011"], ids=str)
def test_numeric_lower_boundaries(client, case):
    headers = auth(client)
    values = {"systolic": 60, "diastolic": 30, "heart_rate": 30}
    record = create(client, headers, **values)
    for key, value in values.items():
        assert record[key] == value
        response = client.post(BASE, headers=headers, json=payload(**{key: value - 1}))
        assert response.status_code == 422, response.text
    assert client.get(BASE, headers=headers).json()["total"] == 1


@pytest.mark.parametrize("case", ["M2-TC-012"], ids=str)
def test_numeric_upper_boundaries(client, case):
    headers = auth(client)
    values = {"systolic": 260, "diastolic": 200, "heart_rate": 220}
    record = create(client, headers, **values)
    for key, value in values.items():
        assert record[key] == value
        response = client.post(BASE, headers=headers, json=payload(**{key: value + 1}))
        assert response.status_code == 422, response.text
    assert client.get(BASE, headers=headers).json()["total"] == 1


@pytest.mark.parametrize("case", ["M2-TC-013"], ids=str)
def test_invalid_heart_rate_update_preserves_record(client, case):
    headers = auth(client)
    record = create(client, headers)
    endpoint = f"{BASE}/{record['id']}"
    for value in [29, 221]:
        response = client.patch(endpoint, headers=headers, json={"heart_rate": value})
        assert response.status_code == 422, response.text
        current = client.get(endpoint, headers=headers)
        assert current.status_code == 200
        assert current.json()["heart_rate"] == 72


@pytest.mark.parametrize("case", ["M2-TC-014"], ids=str)
def test_note_length_boundary_and_rejected_update(client, case):
    headers = auth(client)
    note = "N" * 500
    record = create(client, headers, note=note)
    assert record["note"] == note
    endpoint = f"{BASE}/{record['id']}"
    accepted = client.patch(endpoint, headers=headers, json={"note": "B" * 500})
    assert accepted.status_code == 200
    rejected = client.patch(endpoint, headers=headers, json={"note": "B" * 501})
    assert rejected.status_code == 422
    assert client.get(endpoint, headers=headers).json()["note"] == "B" * 500


@pytest.mark.parametrize("case", ["M2-TC-015"], ids=str)
def test_image_reference_length_boundary(client, case):
    headers = auth(client)
    record = create(client, headers, source="ocr", image_id="I" * 64)
    assert record["image_id"] == "I" * 64
    assert record["source"] == "ocr"
    rejected = client.post(BASE, headers=headers, json=payload(source="ocr", image_id="I" * 65))
    assert rejected.status_code == 422
    assert client.get(BASE, headers=headers).json()["total"] == 1


@pytest.mark.parametrize("case", ["M2-TC-016"], ids=str)
def test_foreign_update_and_delete_do_not_mutate_owner_record(client, case):
    owner, other = auth(client, "bp_owner"), auth(client, "bp_other")
    record = create(client, owner, note="owner only")
    endpoint = f"{BASE}/{record['id']}"
    assert client.patch(endpoint, headers=other, json={"systolic": 200}).status_code == 404
    assert client.delete(endpoint, headers=other).status_code == 404
    current = client.get(endpoint, headers=owner)
    assert current.status_code == 200
    assert current.json()["systolic"] == 120
    assert current.json()["note"] == "owner only"
    assert client.get(BASE, headers=owner).json()["total"] == 1


@pytest.mark.parametrize("case", ["M2-TC-017"], ids=str)
def test_stats_isolation_rounding_and_missing_heart_rate(client, frozen_clock, case):
    owner, other = auth(client, "stats_owner"), auth(client, "stats_other")
    for systolic, diastolic, hr in [(120, 80, None), (121, 82, 71), (124, 85, 74)]:
        create(client, owner, systolic=systolic, diastolic=diastolic, heart_rate=hr)
    create(client, other, systolic=260, diastolic=200, heart_rate=220)
    response = client.get(BASE + "/stats", headers=owner, params={"days": 7})
    assert response.status_code == 200
    assert response.json() == {
        "count": 3, "window_days": 7, "systolic_avg": 121.7,
        "systolic_min": 120, "systolic_max": 124, "diastolic_avg": 82.3,
        "diastolic_min": 80, "diastolic_max": 85, "heart_rate_avg": 72.5,
    }


@pytest.mark.parametrize("case", ["M2-TC-018"], ids=str)
def test_stats_cutoff_microsecond_boundary(client, frozen_clock, case):
    headers = auth(client)
    cutoff = NOW - timedelta(days=7)
    for instant, systolic in [(cutoff - timedelta(microseconds=1), 200),
                              (cutoff, 120), (cutoff + timedelta(microseconds=1), 130)]:
        create(client, headers, systolic=systolic, measured_at=instant.isoformat(), heart_rate=None)
    response = client.get(BASE + "/stats", headers=headers, params={"days": 7})
    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 2
    assert result["systolic_avg"] == 125
    assert result["systolic_min"] == 120 and result["systolic_max"] == 130
    assert result["heart_rate_avg"] is None


@pytest.mark.parametrize("case", ["M2-TC-019"], ids=str)
def test_closed_time_range_and_descending_pagination(client, case):
    headers = auth(client)
    start, end = NOW - timedelta(hours=1), NOW
    ids = []
    for instant in [start - timedelta(microseconds=1), start, end, end + timedelta(microseconds=1)]:
        ids.append(create(client, headers, measured_at=instant.isoformat())["id"])
    params = {"start": start.isoformat(), "end": end.isoformat(), "size": 1}
    for page, expected in [(1, [ids[2]]), (2, [ids[1]]), (3, [])]:
        response = client.get(BASE, headers=headers, params={**params, "page": page})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2 and body["page"] == page and body["size"] == 1
        assert [item["id"] for item in body["items"]] == expected


@pytest.mark.parametrize("case", ["M2-TC-020"], ids=str)
def test_query_parameter_boundaries(client, case):
    headers = auth(client)
    for suffix, key, low, high in [("", "page", 1, None), ("", "size", 1, 200),
                                   ("/stats", "days", 1, 365), ("/forecast", "days", 1, 30)]:
        for value in [low] + ([] if high is None else [high]):
            response = client.get(BASE + suffix, headers=headers, params={key: value})
            assert response.status_code == 200, response.text
        for value in [low - 1] + ([] if high is None else [high + 1]):
            response = client.get(BASE + suffix, headers=headers, params={key: value})
            assert response.status_code == 422, response.text
