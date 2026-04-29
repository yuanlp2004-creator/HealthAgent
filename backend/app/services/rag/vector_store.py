from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import sqlite_vec

from app.core.config import get_settings


@dataclass
class DocMeta:
    doc_id: str
    title: str
    source: str
    url: Optional[str] = None
    published_at: Optional[str] = None
    tags: Optional[list[str]] = None


@dataclass
class ChunkRow:
    chunk_id: int
    doc_id: str
    title: str
    source: str
    url: Optional[str]
    heading_path: str
    ordinal: int
    text: str


def _vec_blob(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _connect(path: Optional[str] = None) -> sqlite3.Connection:
    s = get_settings()
    db_path = path or s.rag_kb_db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection, *, dim: int) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS kb_docs (
            doc_id        TEXT PRIMARY KEY,
            title         TEXT NOT NULL,
            source        TEXT NOT NULL,
            url           TEXT,
            published_at  TEXT,
            tags_json     TEXT,
            content_hash  TEXT,
            ingested_at   TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS kb_chunks (
            chunk_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id        TEXT NOT NULL REFERENCES kb_docs(doc_id) ON DELETE CASCADE,
            heading_path  TEXT NOT NULL,
            ordinal       INTEGER NOT NULL,
            text          TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_kb_chunks_doc ON kb_chunks(doc_id);
        """
    )
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS kb_vectors "
        f"USING vec0(embedding float[{dim}])"
    )
    conn.commit()


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def upsert_document(
    conn: sqlite3.Connection,
    meta: DocMeta,
    chunks: list[tuple[str, int, str, list[float]]],
    *,
    raw_text: str,
) -> int:
    """Insert/replace a document and its chunks+vectors.

    chunks: list of (heading_path, ordinal, text, embedding)
    Returns the number of chunks written.
    """
    digest = _content_hash(raw_text)

    row = conn.execute(
        "SELECT content_hash FROM kb_docs WHERE doc_id = ?", (meta.doc_id,)
    ).fetchone()
    if row is not None and row["content_hash"] == digest:
        return 0

    # wipe old chunks (+ their vectors) for this doc
    old_ids = [
        r["chunk_id"]
        for r in conn.execute(
            "SELECT chunk_id FROM kb_chunks WHERE doc_id = ?", (meta.doc_id,)
        ).fetchall()
    ]
    if old_ids:
        qmarks = ",".join("?" * len(old_ids))
        conn.execute(f"DELETE FROM kb_vectors WHERE rowid IN ({qmarks})", old_ids)
        conn.execute(f"DELETE FROM kb_chunks WHERE chunk_id IN ({qmarks})", old_ids)

    conn.execute(
        """
        INSERT INTO kb_docs(doc_id, title, source, url, published_at, tags_json, content_hash)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(doc_id) DO UPDATE SET
          title=excluded.title, source=excluded.source, url=excluded.url,
          published_at=excluded.published_at, tags_json=excluded.tags_json,
          content_hash=excluded.content_hash, ingested_at=datetime('now')
        """,
        (
            meta.doc_id,
            meta.title,
            meta.source,
            meta.url,
            meta.published_at,
            json.dumps(meta.tags or [], ensure_ascii=False),
            digest,
        ),
    )

    count = 0
    for heading_path, ordinal, text, emb in chunks:
        cur = conn.execute(
            "INSERT INTO kb_chunks(doc_id, heading_path, ordinal, text) VALUES(?,?,?,?)",
            (meta.doc_id, heading_path, ordinal, text),
        )
        conn.execute(
            "INSERT INTO kb_vectors(rowid, embedding) VALUES(?, ?)",
            (cur.lastrowid, _vec_blob(emb)),
        )
        count += 1
    conn.commit()
    return count


def search(
    conn: sqlite3.Connection, query_vec: list[float], top_k: int = 5
) -> list[tuple[ChunkRow, float]]:
    rows = conn.execute(
        """
        SELECT c.chunk_id, c.doc_id, c.heading_path, c.ordinal, c.text,
               d.title, d.source, d.url, v.distance
        FROM kb_vectors v
        JOIN kb_chunks c ON c.chunk_id = v.rowid
        JOIN kb_docs d ON d.doc_id = c.doc_id
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance
        """,
        (_vec_blob(query_vec), top_k),
    ).fetchall()
    out: list[tuple[ChunkRow, float]] = []
    for r in rows:
        out.append(
            (
                ChunkRow(
                    chunk_id=r["chunk_id"],
                    doc_id=r["doc_id"],
                    title=r["title"],
                    source=r["source"],
                    url=r["url"],
                    heading_path=r["heading_path"],
                    ordinal=r["ordinal"],
                    text=r["text"],
                ),
                float(r["distance"]),
            )
        )
    return out


def stats(conn: sqlite3.Connection) -> dict:
    ndocs = conn.execute("SELECT COUNT(*) FROM kb_docs").fetchone()[0]
    nchunks = conn.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0]
    return {"docs": ndocs, "chunks": nchunks}
