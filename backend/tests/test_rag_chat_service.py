from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.rag import chat_service, llm_client, retriever
from app.services.rag.llm_client import ChatMessage
from app.services.rag.retriever import RetrievedCitation


@pytest.fixture(autouse=True)
def _api_key(monkeypatch, tmp_path):
    from app.core.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "dashscope_api_key", "test-key", raising=False)
    monkeypatch.setattr(s, "llm_cache_dir", str(tmp_path / "llmcache"), raising=False)
    monkeypatch.setattr(s, "rag_top_k", 2, raising=False)


def _fake_citations() -> list[RetrievedCitation]:
    return [
        RetrievedCitation(
            idx=1,
            chunk_id=101,
            doc_id="hbp-01",
            title="高血压定义",
            source="占位",
            url=None,
            heading_path="根 / 节",
            text="收缩压 ≥ 140 或舒张压 ≥ 90 可诊断高血压。",
            distance=0.12,
        ),
        RetrievedCitation(
            idx=2,
            chunk_id=102,
            doc_id="hbp-04",
            title="生活方式",
            source="占位",
            url=None,
            heading_path="根",
            text="限盐、运动、戒烟限酒是基础干预。",
            distance=0.18,
        ),
    ]


def _auth_headers(client, username="alice") -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "secret123"},
    )
    return {"Authorization": f"Bearer {r.json()['tokens']['access_token']}"}, r.json()["user"]["id"]


def test_answer_injects_user_context_and_citations(monkeypatch, client):
    from app.db.session import SessionLocal

    h, uid = _auth_headers(client)

    # seed 2 bp records, 1 above threshold
    now = datetime.now(timezone.utc).isoformat()
    client.post(
        "/api/v1/bp-records",
        json={"systolic": 150, "diastolic": 95, "heart_rate": 80, "measured_at": now},
        headers=h,
    )
    client.post(
        "/api/v1/bp-records",
        json={"systolic": 120, "diastolic": 78, "heart_rate": 70, "measured_at": now},
        headers=h,
    )

    captured = {}

    def fake_retrieve(q, *, top_k=5, db_path=None):
        return _fake_citations()

    def fake_chat(messages, *, temperature=None, use_cache=False):
        captured["messages"] = messages
        return "根据资料，收缩压偏高 [1]。建议生活方式干预 [2]。以上内容仅供参考，不构成医疗诊断。"

    monkeypatch.setattr(chat_service, "retrieve", fake_retrieve)
    monkeypatch.setattr(chat_service.llm_client, "chat", fake_chat)

    db = SessionLocal()
    try:
        result = chat_service.answer(db, uid, "我最近血压偏高怎么办？")
    finally:
        db.close()

    assert "[1]" in result.content and "[2]" in result.content
    assert len(result.citations) == 2

    # system prompt present, user message includes both user-context and KB sections
    assert captured["messages"][0].role == "system"
    user_msg = captured["messages"][-1].content
    assert "用户近 14 天血压概况" in user_msg
    assert "其中 1 条读数达到或超过 140/90 mmHg" in user_msg
    assert "知识库片段" in user_msg
    assert "[1] 高血压定义" in user_msg


def test_answer_stream_returns_iter_and_citations(monkeypatch, client):
    from app.db.session import SessionLocal

    h, uid = _auth_headers(client)

    monkeypatch.setattr(chat_service, "retrieve", lambda q, top_k=5, db_path=None: _fake_citations())
    monkeypatch.setattr(
        chat_service.llm_client,
        "chat_stream",
        lambda messages, temperature=None: iter(["部分", "回答"]),
    )

    db = SessionLocal()
    try:
        stream, cits = chat_service.answer_stream(db, uid, "xxx")
    finally:
        db.close()

    assert len(cits) == 2
    assert list(stream) == ["部分", "回答"]


def test_empty_question_short_circuits_retrieval(monkeypatch, client):
    from app.db.session import SessionLocal

    h, uid = _auth_headers(client)
    called = {"n": 0}

    def bad_embed(*a, **kw):
        called["n"] += 1
        return [[0.0]]

    monkeypatch.setattr(llm_client, "embed", bad_embed)
    cits = retriever.retrieve("   ")
    assert cits == []
    assert called["n"] == 0
