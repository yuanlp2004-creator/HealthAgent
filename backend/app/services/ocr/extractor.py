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
    fields = OCRFields()
    chosen: list[FieldCandidate] = []
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
