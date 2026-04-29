from __future__ import annotations

import re
from dataclasses import dataclass


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass
class Chunk:
    text: str
    heading_path: str  # e.g. "一级 / 二级"
    ordinal: int


def _split_sections(md: str) -> list[tuple[str, str]]:
    """Return [(heading_path, body)] — splits on markdown headings, keeping the
    nearest ancestor chain as the heading path."""
    lines = md.splitlines()
    stack: list[tuple[int, str]] = []  # (level, title)
    sections: list[tuple[str, list[str]]] = []
    current_body: list[str] = []
    current_path = ""

    def flush():
        if current_body and any(line.strip() for line in current_body):
            sections.append((current_path, list(current_body)))

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            flush()
            current_body.clear()
            level = len(m.group(1))
            title = m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            current_path = " / ".join(t for _, t in stack)
        else:
            current_body.append(line)
    flush()

    return [(path, "\n".join(body).strip()) for path, body in sections if "\n".join(body).strip()]


def _window(text: str, size: int, overlap: int) -> list[str]:
    """Character-window slicing with overlap. size/overlap measured in characters
    (CJK-friendly vs token splitting). Keeps paragraphs when possible by preferring
    newline boundaries within the last 20% of each window."""
    if len(text) <= size:
        return [text]
    out: list[str] = []
    i = 0
    n = len(text)
    step = max(1, size - overlap)
    while i < n:
        end = min(n, i + size)
        if end < n:
            # try to break on paragraph/sentence boundary near the tail
            soft_zone = text[end - max(1, size // 5) : end]
            for sep in ("\n\n", "\n", "。", "；", "."):
                idx = soft_zone.rfind(sep)
                if idx != -1:
                    end = end - (len(soft_zone) - idx - len(sep))
                    break
        out.append(text[i:end].strip())
        if end >= n:
            break
        i = max(end - overlap, i + step)
    return [c for c in out if c]


def chunk_markdown(md: str, *, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split markdown into heading-aware character windows."""
    sections = _split_sections(md) or [("", md.strip())]
    out: list[Chunk] = []
    ordinal = 0
    for path, body in sections:
        for piece in _window(body, size, overlap):
            if not piece.strip():
                continue
            out.append(Chunk(text=piece, heading_path=path, ordinal=ordinal))
            ordinal += 1
    return out
