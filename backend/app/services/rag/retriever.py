from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.services.rag import llm_client
from app.services.rag.vector_store import ChunkRow, _connect


@dataclass
class RetrievedCitation:
    idx: int  # 1-based, for [1][2]… citation markers
    chunk_id: int
    doc_id: str
    title: str
    source: str
    url: Optional[str]
    heading_path: str
    text: str
    distance: float


def retrieve(query: str, *, top_k: int = 5, db_path: Optional[str] = None) -> list[RetrievedCitation]:
    if not query.strip():
        return []
    vec = llm_client.embed([query])[0]
    conn = _connect(db_path)
    try:
        from app.services.rag.vector_store import search

        raw = search(conn, vec, top_k=top_k)
    finally:
        conn.close()
    out: list[RetrievedCitation] = []
    for i, (row, dist) in enumerate(raw, start=1):
        out.append(
            RetrievedCitation(
                idx=i,
                chunk_id=row.chunk_id,
                doc_id=row.doc_id,
                title=row.title,
                source=row.source,
                url=row.url,
                heading_path=row.heading_path,
                text=row.text,
                distance=dist,
            )
        )
    return out
