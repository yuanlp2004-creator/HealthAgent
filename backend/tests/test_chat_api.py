from __future__ import annotations

import json

import pytest

from app.services.rag.retriever import RetrievedCitation


VALID = {"username": "alice", "email": "alice@example.com", "password": "secret123"}
OTHER = {"username": "bob", "email": "bob@example.com", "password": "secret123"}


def _register_and_auth(client, payload=VALID):
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['tokens']['access_token']}"}


@pytest.fixture
def _mock_rag(monkeypatch):
    from app.services.rag import chat_service

    def fake_stream(db, user_id, question, history=None):
        citations = [
            RetrievedCitation(
                idx=1, chunk_id=1, doc_id="hbp-01", title="高血压定义",
                source="占位", url=None, heading_path="", text="收缩压≥140",
                distance=0.1,
            ),
        ]
        return iter(["你好", "，这是回答。"]), citations

    monkeypatch.setattr(chat_service, "answer_stream", fake_stream)
    yield


class TestConversationCrud:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/chat/conversations").status_code == 401
        assert client.post("/api/v1/chat/conversations", json={}).status_code == 401

    def test_create_and_list(self, client):
        h = _register_and_auth(client)
        r = client.post("/api/v1/chat/conversations", json={"title": "高血压咨询"}, headers=h)
        assert r.status_code == 201
        conv_id = r.json()["id"]

        lst = client.get("/api/v1/chat/conversations", headers=h).json()
        assert any(c["id"] == conv_id for c in lst["items"])

    def test_user_isolation(self, client):
        ha = _register_and_auth(client, VALID)
        hb = _register_and_auth(client, OTHER)
        conv_id = client.post("/api/v1/chat/conversations", json={}, headers=ha).json()["id"]
        assert client.get(
            f"/api/v1/chat/conversations/{conv_id}/messages", headers=hb
        ).status_code == 404
        assert client.delete(
            f"/api/v1/chat/conversations/{conv_id}", headers=hb
        ).status_code == 404

    def test_delete(self, client):
        h = _register_and_auth(client)
        conv_id = client.post("/api/v1/chat/conversations", json={}, headers=h).json()["id"]
        assert client.delete(f"/api/v1/chat/conversations/{conv_id}", headers=h).status_code == 204
        assert client.get(
            f"/api/v1/chat/conversations/{conv_id}/messages", headers=h
        ).status_code == 404


class TestAskSse:
    def test_ask_streams_and_persists(self, client, _mock_rag):
        h = _register_and_auth(client)
        conv_id = client.post("/api/v1/chat/conversations", json={}, headers=h).json()["id"]

        with client.stream(
            "POST",
            f"/api/v1/chat/conversations/{conv_id}/ask",
            json={"question": "什么是高血压？"},
            headers=h,
        ) as resp:
            assert resp.status_code == 200
            body = b"".join(chunk for chunk in resp.iter_bytes()).decode("utf-8")

        assert "event: citations" in body
        assert "event: delta" in body
        assert "event: done" in body
        assert "高血压定义" in body
        # assembled reply contains both deltas
        assert "你好" in body and "这是回答" in body

        msgs = client.get(
            f"/api/v1/chat/conversations/{conv_id}/messages", headers=h
        ).json()["items"]
        roles = [m["role"] for m in msgs]
        assert roles == ["user", "assistant"]
        assert msgs[0]["content"] == "什么是高血压？"
        assert msgs[1]["content"] == "你好，这是回答。"
        assert len(msgs[1]["citations"]) == 1
        assert msgs[1]["citations"][0]["title"] == "高血压定义"

    def test_ask_404_on_foreign_conv(self, client, _mock_rag):
        ha = _register_and_auth(client, VALID)
        hb = _register_and_auth(client, OTHER)
        conv_id = client.post("/api/v1/chat/conversations", json={}, headers=ha).json()["id"]
        r = client.post(
            f"/api/v1/chat/conversations/{conv_id}/ask",
            json={"question": "x"},
            headers=hb,
        )
        assert r.status_code == 404

    def test_ask_empty_question_422(self, client):
        h = _register_and_auth(client)
        conv_id = client.post("/api/v1/chat/conversations", json={}, headers=h).json()["id"]
        r = client.post(
            f"/api/v1/chat/conversations/{conv_id}/ask",
            json={"question": ""},
            headers=h,
        )
        assert r.status_code == 422
