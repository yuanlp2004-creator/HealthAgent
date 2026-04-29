"""Knowledge-base CLI: `python -m app.cli.kb ingest <path>`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.services.rag.ingest import ingest_dir, ingest_file
from app.services.rag.vector_store import _connect, init_db, stats
from app.core.config import get_settings


def cmd_ingest(args) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"[error] path does not exist: {path}", file=sys.stderr)
        return 2

    if path.is_dir():
        results = ingest_dir(path, db_path=args.db)
    else:
        results = [ingest_file(path, db_path=args.db)]

    for r in results:
        status = "skip" if r.skipped else f"+{r.chunks_written}"
        print(f"  [{status:>6}] {r.doc_id} — {r.title}")

    written = sum(r.chunks_written for r in results)
    skipped = sum(1 for r in results if r.skipped)
    print(f"done: {len(results)} files, {written} chunks written, {skipped} skipped")
    return 0


def cmd_stats(args) -> int:
    s = get_settings()
    conn = _connect(args.db)
    try:
        init_db(conn, dim=s.dashscope_embedding_dim)
        info = stats(conn)
    finally:
        conn.close()
    print(f"docs: {info['docs']}, chunks: {info['chunks']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli.kb")
    parser.add_argument("--db", default=None, help="sqlite path (default: settings)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ing = sub.add_parser("ingest", help="ingest md file or directory")
    p_ing.add_argument("path")
    p_ing.set_defaults(func=cmd_ingest)

    p_stat = sub.add_parser("stats", help="print kb stats")
    p_stat.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
