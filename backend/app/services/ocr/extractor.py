from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional

INT_RE = re.compile(r"\d{2,3}")

SYS_RANGE = (60, 250)
DIA_RANGE = (30, 160)
HR_RANGE = (30, 200)


@dataclass
class NumberToken:
    value: int
    y: float
    x: float
    confidence: float
    raw: str
    height: float = 0.0


@dataclass
class FieldCandidate:
    label: str
    value: int
    confidence: float


@dataclass
class OCRFields:
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    heart_rate: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OCRResult:
    raw_text: str
    tokens: list[NumberToken] = field(default_factory=list)
    candidates: list[FieldCandidate] = field(default_factory=list)
    fields: OCRFields = field(default_factory=OCRFields)


def _in_range(value: int, rng: tuple[int, int]) -> bool:
    return rng[0] <= value <= rng[1]


def parse_tokens(ocr_lines: list) -> list[NumberToken]:
    tokens: list[NumberToken] = []
    for box, (text, conf) in ocr_lines:
        for match in INT_RE.finditer(text):
            raw = match.group(0)
            v = int(raw)
            if not (20 <= v <= 260):
                continue
            cx = sum(p[0] for p in box) / 4
            cy = sum(p[1] for p in box) / 4
            ys = [p[1] for p in box]
            height = max(ys) - min(ys)
            tokens.append(NumberToken(value=v, y=cy, x=cx, confidence=float(conf), raw=raw, height=height))
    return tokens


def _x_cluster_assign(sorted_tokens: list[NumberToken]) -> OCRFields | None:
    """Try X-coordinate clustering to separate main column (SYS+DIA) from side (HR).

    On smartphone/app layouts, SYS and DIA share a left column while HR sits on the
    right at a similar Y to SYS.  Pure Y-sorting swaps DIA/HR in that case.
    Returns None if clustering is ambiguous (fall back to Y-only logic).
    """
    if len(sorted_tokens) < 3:
        return None
    xs = [t.x for t in sorted_tokens]
    median_x = sorted(xs)[len(xs) // 2]
    main = [t for t in sorted_tokens if abs(t.x - median_x) < 150]
    side = [t for t in sorted_tokens if abs(t.x - median_x) >= 150]
    if len(main) < 2 or len(side) != 1:
        return None

    # Safety: main tokens must truly cluster (X spread < 100px) and
    # side token must be clearly separated (>= 200px from median)
    main_xs = [t.x for t in main]
    if max(main_xs) - min(main_xs) > 100:
        return None
    if abs(side[0].x - median_x) < 200:
        return None

    main_sorted = sorted(main, key=lambda t: t.y)
    hr_cand = side[0]

    sys_cand = None
    dia_cand = None
    for t in main_sorted:
        if _in_range(t.value, SYS_RANGE):
            if sys_cand is None:
                sys_cand = t
            elif dia_cand is None:
                dia_cand = t
        elif _in_range(t.value, DIA_RANGE) and dia_cand is None:
            dia_cand = t

    if sys_cand is None:
        sys_cand = main_sorted[0]
        dia_cand = main_sorted[1] if len(main_sorted) > 1 else None
    elif dia_cand is None and len(main_sorted) > 1:
        dia_cand = main_sorted[0] if main_sorted[0] != sys_cand else main_sorted[1]

    if sys_cand is None or dia_cand is None or hr_cand is None:
        return None
    if not _in_range(sys_cand.value, SYS_RANGE) or not _in_range(dia_cand.value, DIA_RANGE):
        return None
    if sys_cand.value <= dia_cand.value:
        return None
    if not _in_range(hr_cand.value, HR_RANGE):
        return None

    return OCRFields(systolic=sys_cand.value, diastolic=dia_cand.value, heart_rate=hr_cand.value)


def extract_fields(tokens: list[NumberToken]) -> tuple[OCRFields, list[FieldCandidate]]:
    filtered = tokens
    if tokens:
        max_h = max(t.height for t in tokens) or 0.0
        if max_h > 0:
            threshold = max_h * 0.4
            big = [t for t in tokens if t.height >= threshold]
            if big:
                filtered = big

    sorted_tokens = sorted(filtered, key=lambda t: t.y)

    # Try X-clustering first (handles smartphone/app layouts with side HR)
    fields = _x_cluster_assign(sorted_tokens)
    if fields is not None:
        chosen: list[FieldCandidate] = []
        for label in ("systolic", "diastolic", "heart_rate"):
            v = getattr(fields, label)
            if v is not None:
                tok = next((t for t in sorted_tokens if t.value == v), None)
                conf = tok.confidence if tok else 0.99
                chosen.append(FieldCandidate(label=label, value=v, confidence=conf))
        return fields, chosen

    # Fallback: Y-only greedy assignment (works for LCD monitors)
    fields = OCRFields()
    chosen = []
    used: set[int] = set()
    last_y = -float("inf")

    plan = [
        ("systolic", SYS_RANGE),
        ("diastolic", DIA_RANGE),
        ("heart_rate", HR_RANGE),
    ]
    for label, rng in plan:
        for idx, tok in enumerate(sorted_tokens):
            if idx in used:
                continue
            if tok.y <= last_y:
                continue
            if not _in_range(tok.value, rng):
                continue
            setattr(fields, label, tok.value)
            chosen.append(FieldCandidate(label=label, value=tok.value, confidence=tok.confidence))
            used.add(idx)
            last_y = tok.y
            break

    if fields.systolic is not None and fields.diastolic is not None:
        if fields.systolic <= fields.diastolic:
            fields.diastolic = None
            chosen = [c for c in chosen if c.label != "diastolic"]

    return fields, chosen
