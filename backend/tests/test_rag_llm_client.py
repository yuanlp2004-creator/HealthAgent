from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Iterable

import pytest

from app.services.rag import llm_client
from app.services.rag.llm_client import ChatMessage, LLMError


class _FakeResp:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text or json.dumps(self._body)

    def json(self):
        return self._body


class _StreamResp:
    def __init__(self, lines, status_code=200, text=""):
        self.status_code = status_code
        self._lines = lines
        self.text = text

    def iter_lines(self, decode_unicode=True):
        yield from self._lines

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture(autouse=True)
def _key(monkeypatch, tmp_path):
    from app.core.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "dashscope_api_key", "test-key", raising=False)
    monkeypatch.setattr(s, "llm_cache_dir", str(tmp_path / "cache"), raising=False)
    yield


class TestEmbed:
    def test_returns_vectors_for_batch(self, monkeypatch):
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured["json"] = json
            return _FakeResp(
                body={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]}
            )

        monkeypatch.setattr(llm_client.requests, "post", fake_post)
        vecs = llm_client.embed(["hello", "world"], use_cache=False)
        assert vecs == [[0.1, 0.2], [0.3, 0.4]]
        assert captured["json"]["input"] == ["hello", "world"]

    def test_cache_skips_network_on_repeat(self, monkeypatch):
        calls = {"n": 0}

        def fake_post(url, headers=None, json=None, timeout=None):
            calls["n"] += 1
            return _FakeResp(body={"data": [{"embedding": [1.0]}]})

        monkeypatch.setattr(llm_client.requests, "post", fake_post)
        llm_client.embed(["hi"])
        llm_client.embed(["hi"])
        assert calls["n"] == 1

    def test_empty_input_no_network(self, monkeypatch):
        def fail_post(*a, **kw):
            raise AssertionError("should not call")

        monkeypatch.setattr(llm_client.requests, "post", fail_post)
        assert llm_client.embed([]) == []

    def test_error_on_non_200(self, monkeypatch):
        monkeypatch.setattr(
            llm_client.requests, "post", lambda *a, **kw: _FakeResp(status_code=500, text="boom")
        )
        with pytest.raises(LLMError):
            llm_client.embed(["x"], use_cache=False)

    def test_error_when_missing_key(self, monkeypatch):
        from app.core.config import get_settings

        s = get_settings()
        monkeypatch.setattr(s, "dashscope_api_key", "", raising=False)
        with pytest.raises(LLMError):
            llm_client.embed(["x"], use_cache=False)


class TestChat:
    def test_returns_content(self, monkeypatch):
        monkeypatch.setattr(
            llm_client.requests,
            "post",
            lambda *a, **kw: _FakeResp(
                body={"choices": [{"message": {"content": "hello"}}]}
            ),
        )
        out = llm_client.chat([ChatMessage("user", "hi")])
        assert out == "hello"

    def test_error_on_malformed_body(self, monkeypatch):
        monkeypatch.setattr(
            llm_client.requests, "post", lambda *a, **kw: _FakeResp(body={"nope": 1})
        )
        with pytest.raises(LLMError):
            llm_client.chat([ChatMessage("user", "hi")])


class TestChatStream:
    def test_yields_deltas_and_stops_on_done(self, monkeypatch):
        lines = [
            "data: " + json.dumps({"choices": [{"delta": {"content": "你"}}]}),
            "",
            "data: " + json.dumps({"choices": [{"delta": {"content": "好"}}]}),
            "data: [DONE]",
            "data: " + json.dumps({"choices": [{"delta": {"content": "ignored"}}]}),
        ]
        monkeypatch.setattr(
            llm_client.requests, "post", lambda *a, **kw: _StreamResp(lines)
        )
        out = list(llm_client.chat_stream([ChatMessage("user", "q")]))
        assert out == ["你", "好"]

    def test_error_on_non_200(self, monkeypatch):
        monkeypatch.setattr(
            llm_client.requests,
            "post",
            lambda *a, **kw: _StreamResp([], status_code=502, text="bad"),
        )
        with pytest.raises(LLMError):
            list(llm_client.chat_stream([ChatMessage("user", "q")]))
