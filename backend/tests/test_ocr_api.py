import io

import numpy as np
import pytest

from app.services import ocr_service
from app.services.ocr.extractor import FieldCandidate, OCRFields, OCRResult


VALID_PAYLOAD = {
    "username": "bob",
    "email": "bob@example.com",
    "password": "secret123",
}


def _png_bytes(w: int = 400, h: int = 300) -> bytes:
    import cv2
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


@pytest.fixture()
def token(client):
    r = client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    assert r.status_code == 201
    return r.json()["tokens"]["access_token"]


@pytest.fixture(autouse=True)
def stub_ocr(monkeypatch):
    def fake_recognize(_data: bytes) -> OCRResult:
        fields = OCRFields(systolic=138, diastolic=91, heart_rate=102)
        cands = [
            FieldCandidate("systolic", 138, 0.95),
            FieldCandidate("diastolic", 91, 0.93),
            FieldCandidate("heart_rate", 102, 0.9),
        ]
        return OCRResult(raw_text="138\n91\n102", candidates=cands, fields=fields)
    monkeypatch.setattr(ocr_service, "recognize", fake_recognize)


def test_ocr_bp_requires_auth(client):
    r = client.post(
        "/api/v1/ocr/bp",
        files={"file": ("x.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 401


def test_ocr_bp_rejects_unsupported_type(client, token):
    r = client.post(
        "/api/v1/ocr/bp",
        files={"file": ("x.txt", b"hello", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 415


def test_ocr_bp_rejects_empty_file(client, token):
    r = client.post(
        "/api/v1/ocr/bp",
        files={"file": ("x.png", b"", "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_ocr_bp_success(client, token, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = client.post(
        "/api/v1/ocr/bp",
        files={"file": ("x.png", _png_bytes(), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fields"] == {"systolic": 138, "diastolic": 91, "heart_rate": 102}
    assert len(body["candidates"]) == 3
    assert body["image_id"]
    assert body["raw_text"]
    saved = list((tmp_path / "storage" / "images").rglob("*.png"))
    assert len(saved) == 1


def test_ocr_bp_too_large(client, token, monkeypatch):
    from app.api.v1 import ocr as ocr_mod
    monkeypatch.setattr(ocr_mod, "MAX_BYTES", 10)
    r = client.post(
        "/api/v1/ocr/bp",
        files={"file": ("x.png", _png_bytes(), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 413
