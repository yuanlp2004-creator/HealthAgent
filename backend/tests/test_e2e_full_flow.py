"""端到端集成测试：注册 → 登录 → OCR → 入库 → 看板 → 问诊。

覆盖 00 总计划 §P7 "关键场景"要求的完整链路。外部依赖（VLM、LLM、
Embedding）全部 mock，只验证各模块之间的接口契约对齐与鉴权贯通。
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from app.services import ocr_service
from app.services.ocr.extractor import FieldCandidate, OCRFields, OCRResult
from app.services.rag import chat_service
from app.services.rag.retriever import RetrievedCitation


USER = {"username": "e2e_user", "email": "e2e@example.com", "password": "secret123"}


def _png_bytes(w: int = 400, h: int = 300) -> bytes:
    import cv2
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


@pytest.fixture()
def stub_vlm(monkeypatch):
    def fake_recognize(_data: bytes) -> OCRResult:
        fields = OCRFields(systolic=135, diastolic=88, heart_rate=78)
        cands = [
            FieldCandidate("systolic", 135, 0.96),
            FieldCandidate("diastolic", 88, 0.94),
            FieldCandidate("heart_rate", 78, 0.9),
        ]
        return OCRResult(raw_text="135\n88\n78", candidates=cands, fields=fields)
    monkeypatch.setattr(ocr_service, "recognize", fake_recognize)


@pytest.fixture()
def stub_llm(monkeypatch):
    def fake_stream(db, user_id, question, history=None):
        citations = [
            RetrievedCitation(
                idx=1, chunk_id=1, doc_id="hbp-01", title="高血压定义与分级",
                source="占位", url=None, heading_path="高血压/定义",
                text="收缩压 ≥ 140 mmHg 或舒张压 ≥ 90 mmHg 为高血压",
                distance=0.12,
            ),
        ]
        return iter(["您的血压略高", "，建议持续监测 [1]。", "以上内容仅供参考，不构成医疗诊断。"]), citations

    monkeypatch.setattr(chat_service, "answer_stream", fake_stream)


def test_full_user_journey(client, stub_vlm, stub_llm, tmp_path, monkeypatch):
    """注册 → 登录 → OCR → 入库 → 看板 → 会话 → 问诊 全链路。"""
    monkeypatch.chdir(tmp_path)

    # --- 1) 注册 ---
    reg = client.post("/api/v1/auth/register", json=USER)
    assert reg.status_code == 201, reg.text
    assert reg.json()["user"]["username"] == USER["username"]

    # --- 2) 登录（忽略注册返回的 token，验证登录独立可用）---
    login = client.post(
        "/api/v1/auth/login",
        json={"username": USER["username"], "password": USER["password"]},
    )
    assert login.status_code == 200, login.text
    access = login.json()["tokens"]["access_token"]
    h = {"Authorization": f"Bearer {access}"}

    # --- 2.5) /users/me 验证 token 有效 ---
    me = client.get("/api/v1/users/me", headers=h)
    assert me.status_code == 200
    assert me.json()["username"] == USER["username"]

    # --- 3) OCR 识别 ---
    ocr = client.post(
        "/api/v1/ocr/bp",
        files={"file": ("bp.png", _png_bytes(), "image/png")},
        headers=h,
    )
    assert ocr.status_code == 200, ocr.text
    ocr_body = ocr.json()
    assert ocr_body["fields"] == {"systolic": 135, "diastolic": 88, "heart_rate": 78}
    image_id = ocr_body["image_id"]
    assert image_id

    # --- 4) OCR 结果入库 ---
    create = client.post(
        "/api/v1/bp-records",
        json={
            "systolic": ocr_body["fields"]["systolic"],
            "diastolic": ocr_body["fields"]["diastolic"],
            "heart_rate": ocr_body["fields"]["heart_rate"],
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "source": "ocr",
            "image_id": image_id,
            "note": "e2e 拍照录入",
        },
        headers=h,
    )
    assert create.status_code == 201, create.text
    rec = create.json()
    assert rec["source"] == "ocr"
    assert rec["image_id"] == image_id
    rec_id = rec["id"]

    # --- 5) 看板：列表 + stats ---
    lst = client.get("/api/v1/bp-records", headers=h).json()
    assert lst["total"] == 1
    assert lst["items"][0]["id"] == rec_id

    stats = client.get("/api/v1/bp-records/stats", headers=h)
    assert stats.status_code == 200
    stats_body = stats.json()
    assert stats_body["count"] >= 1

    # --- 6) 创建会话 ---
    conv = client.post("/api/v1/chat/conversations", json={"title": "e2e 咨询"}, headers=h)
    assert conv.status_code == 201, conv.text
    conv_id = conv.json()["id"]

    # --- 7) SSE 问诊 ---
    with client.stream(
        "POST",
        f"/api/v1/chat/conversations/{conv_id}/ask",
        json={"question": "我这个血压偏高吗？"},
        headers=h,
    ) as resp:
        assert resp.status_code == 200
        body = b"".join(resp.iter_bytes()).decode("utf-8")

    assert "event: citations" in body
    assert "event: delta" in body
    assert "event: done" in body
    assert "高血压定义与分级" in body
    assert "仅供参考" in body

    # --- 8) 消息持久化 + 引用落库 ---
    msgs = client.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=h).json()["items"]
    roles = [m["role"] for m in msgs]
    assert roles == ["user", "assistant"]
    assert msgs[0]["content"] == "我这个血压偏高吗？"
    assert "您的血压略高" in msgs[1]["content"]
    assert len(msgs[1]["citations"]) == 1
    assert msgs[1]["citations"][0]["title"] == "高血压定义与分级"

    # --- 9) 清理：删除记录 + 删除会话 ---
    assert client.delete(f"/api/v1/bp-records/{rec_id}", headers=h).status_code == 204
    assert client.delete(f"/api/v1/chat/conversations/{conv_id}", headers=h).status_code == 204
    assert client.get("/api/v1/bp-records", headers=h).json()["total"] == 0


def test_unauthenticated_cannot_cross_modules(client):
    """未登录时所有业务接口统一 401。"""
    assert client.get("/api/v1/users/me").status_code == 401
    assert client.get("/api/v1/bp-records").status_code == 401
    assert client.get("/api/v1/bp-records/stats").status_code == 401
    assert client.get("/api/v1/chat/conversations").status_code == 401
    assert client.post(
        "/api/v1/ocr/bp",
        files={"file": ("x.png", _png_bytes(), "image/png")},
    ).status_code == 401
