from __future__ import annotations

from pathlib import Path

import pytest

from app.services.rag import ingest as ingest_mod
from app.services.rag import llm_client
from app.services.rag.ingest import ingest_dir, ingest_file
from app.services.rag.vector_store import _connect, init_db, search, stats


@pytest.fixture
def kb_db(tmp_path):
    return str(tmp_path / "kb.sqlite")


@pytest.fixture(autouse=True)
def _api_key(monkeypatch, tmp_path):
    from app.core.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "dashscope_api_key", "test-key", raising=False)
    monkeypatch.setattr(s, "llm_cache_dir", str(tmp_path / "llmcache"), raising=False)
    monkeypatch.setattr(s, "rag_chunk_size", 200, raising=False)
    monkeypatch.setattr(s, "rag_chunk_overlap", 20, raising=False)
    monkeypatch.setattr(s, "dashscope_embedding_dim", 4, raising=False)


def _fake_embed(seed: int):
    # deterministic non-trivial vectors per text
    def _f(texts, use_cache=True):
        out = []
        for i, t in enumerate(texts):
            h = sum(ord(c) for c in t) + seed
            out.append([(h + i) % 7 / 7.0, (h + i) % 11 / 11.0, 0.1, 0.2])
        return out

    return _f


def test_ingest_file_writes_chunks_and_search_returns_hit(monkeypatch, kb_db, tmp_path):
    monkeypatch.setattr(llm_client, "embed", _fake_embed(1))

    doc = tmp_path / "doc.md"
    doc.write_text(
        "---\n"
        "doc_id: hbp-basics\n"
        "title: 高血压基础\n"
        "source: WHO\n"
        "url: https://example.org/hbp\n"
        "tags: [hbp, basics]\n"
        "---\n"
        "# 高血压\n"
        "## 定义\n"
        "高血压是指体循环动脉血压持续升高的状态。\n\n"
        "## 危险因素\n"
        "高盐饮食、肥胖、缺乏运动是主要诱因。\n",
        encoding="utf-8",
    )

    result = ingest_file(doc, db_path=kb_db)
    assert result.doc_id == "hbp-basics"
    assert result.skipped is False
    assert result.chunks_written >= 2

    conn = _connect(kb_db)
    try:
        from app.core.config import get_settings

        init_db(conn, dim=get_settings().dashscope_embedding_dim)
        info = stats(conn)
        assert info["docs"] == 1
        assert info["chunks"] == result.chunks_written

        qvec = _fake_embed(1)(["危险因素"])[0]
        hits = search(conn, qvec, top_k=3)
        assert hits, "expected at least one hit"
        titles = {h.title for h, _ in hits}
        assert "高血压基础" in titles
    finally:
        conn.close()


def test_reingest_same_content_is_skipped(monkeypatch, kb_db, tmp_path):
    monkeypatch.setattr(llm_client, "embed", _fake_embed(2))
    doc = tmp_path / "doc.md"
    doc.write_text("# T\n内容一段\n", encoding="utf-8")

    r1 = ingest_file(doc, db_path=kb_db)
    assert r1.skipped is False

    calls = {"n": 0}
    orig = _fake_embed(2)

    def counting(texts, use_cache=True):
        calls["n"] += 1
        return orig(texts, use_cache=use_cache)

    monkeypatch.setattr(llm_client, "embed", counting)
    r2 = ingest_file(doc, db_path=kb_db)
    assert r2.skipped is True
    assert calls["n"] == 0  # short-circuit before embedding


def test_reingest_changed_content_replaces_chunks(monkeypatch, kb_db, tmp_path):
    monkeypatch.setattr(llm_client, "embed", _fake_embed(3))
    doc = tmp_path / "doc.md"
    doc.write_text("# T\n第一版内容\n", encoding="utf-8")
    ingest_file(doc, db_path=kb_db)

    doc.write_text("# T\n全新内容，长度不同且更长更长更长\n", encoding="utf-8")
    r = ingest_file(doc, db_path=kb_db)
    assert r.skipped is False

    conn = _connect(kb_db)
    try:
        from app.core.config import get_settings

        init_db(conn, dim=get_settings().dashscope_embedding_dim)
        info = stats(conn)
        # exactly one doc, old chunks replaced
        assert info["docs"] == 1
        texts = [
            r["text"]
            for r in conn.execute("SELECT text FROM kb_chunks").fetchall()
        ]
        assert all("第一版" not in t for t in texts)
    finally:
        conn.close()


def test_ingest_dir_processes_multiple(monkeypatch, kb_db, tmp_path):
    monkeypatch.setattr(llm_client, "embed", _fake_embed(4))
    for i in range(3):
        (tmp_path / f"d{i}.md").write_text(f"# 文档{i}\n正文{i}\n", encoding="utf-8")
    results = ingest_dir(tmp_path, db_path=kb_db)
    assert len(results) == 3
    assert all(not r.skipped for r in results)
