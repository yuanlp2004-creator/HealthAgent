from __future__ import annotations

import pytest

from app.services.rag.chunker import chunk_markdown


def test_short_doc_single_chunk():
    out = chunk_markdown("短文本，没有标题。", size=500, overlap=50)
    assert len(out) == 1
    assert out[0].heading_path == ""


def test_splits_by_headings_preserves_path():
    md = (
        "# 根\n"
        "介绍段落\n\n"
        "## 子节 A\n"
        "内容 A\n\n"
        "## 子节 B\n"
        "内容 B\n"
    )
    out = chunk_markdown(md, size=500, overlap=50)
    paths = [c.heading_path for c in out]
    assert "根" in paths
    assert "根 / 子节 A" in paths
    assert "根 / 子节 B" in paths


def test_long_section_gets_windowed():
    body = "。".join(f"第{i}句话内容填充" for i in range(200))
    md = f"# 章节\n{body}\n"
    out = chunk_markdown(md, size=300, overlap=30)
    assert len(out) >= 3
    # overlap: consecutive windows share prefix/suffix within section
    for c in out:
        assert c.heading_path == "章节"


def test_deeper_heading_pops_shallower_siblings():
    md = (
        "# A\n"
        "## A.1\n"
        "aa1\n"
        "## A.2\n"
        "aa2\n"
        "# B\n"
        "bb\n"
    )
    out = chunk_markdown(md, size=500, overlap=50)
    paths = {c.heading_path for c in out}
    assert "A / A.1" in paths
    assert "A / A.2" in paths
    assert "B" in paths
    assert not any("A.1" in p and "B" in p for p in paths)
