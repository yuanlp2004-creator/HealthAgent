from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from app.core.config import get_settings
from app.services.rag import llm_client
from app.services.rag.chunker import chunk_markdown
from app.services.rag.vector_store import DocMeta, _connect, init_db, upsert_document


FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class IngestResult:
    doc_id: str
    title: str
    chunks_written: int
    skipped: bool  # True when content hash matches and nothing changed


def _parse_front_matter(text: str) -> tuple[dict, str]:
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), m.group(2)


def _slug_from_path(p: Path) -> str:
    return p.stem


def ingest_file(path: Path, *, db_path: Optional[str] = None) -> IngestResult:
    raw = Path(path).read_text(encoding="utf-8")
    meta_dict, body = _parse_front_matter(raw)

    s = get_settings()
    doc_id = str(meta_dict.get("doc_id") or _slug_from_path(Path(path)))
    title = str(meta_dict.get("title") or doc_id)
    source = str(meta_dict.get("source") or "unknown")
    url = meta_dict.get("url")
    published_at = meta_dict.get("published_at")
    tags = meta_dict.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    chunks = chunk_markdown(body, size=s.rag_chunk_size, overlap=s.rag_chunk_overlap)
    if not chunks:
        return IngestResult(doc_id=doc_id, title=title, chunks_written=0, skipped=True)

    conn = _connect(db_path)
    try:
        init_db(conn, dim=s.dashscope_embedding_dim)

        # Short-circuit if content unchanged — avoids unnecessary embedding calls.
        import hashlib

        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        row = conn.execute(
            "SELECT content_hash FROM kb_docs WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        if row is not None and row["content_hash"] == digest:
            return IngestResult(doc_id=doc_id, title=title, chunks_written=0, skipped=True)

        vectors = llm_client.embed([c.text for c in chunks])
        if len(vectors) != len(chunks):
            raise RuntimeError(
                f"embedding/chunk count mismatch: {len(vectors)} vs {len(chunks)}"
            )

        rows = [
            (c.heading_path, c.ordinal, c.text, v) for c, v in zip(chunks, vectors)
        ]
        written = upsert_document(
            conn,
            DocMeta(
                doc_id=doc_id,
                title=title,
                source=source,
                url=url,
                published_at=str(published_at) if published_at else None,
                tags=tags,
            ),
            rows,
            raw_text=body,
        )
        return IngestResult(doc_id=doc_id, title=title, chunks_written=written, skipped=False)
    finally:
        conn.close()


def ingest_dir(root: Path, *, db_path: Optional[str] = None) -> list[IngestResult]:
    root = Path(root)
    results: list[IngestResult] = []
    for p in sorted(root.rglob("*.md")):
        results.append(ingest_file(p, db_path=db_path))
    return results
