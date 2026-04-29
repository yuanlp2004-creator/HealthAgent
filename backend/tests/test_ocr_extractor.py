from app.services.ocr.extractor import (
    NumberToken,
    extract_fields,
    parse_tokens,
)


def _box(cx: float, cy: float):
    return [[cx - 10, cy - 10], [cx + 10, cy - 10], [cx + 10, cy + 10], [cx - 10, cy + 10]]


def test_parse_tokens_filters_non_numeric_and_out_of_range():
    lines = [
        (_box(100, 100), ("abc", 0.9)),
        (_box(100, 120), ("5", 0.9)),
        (_box(100, 140), ("12", 0.8)),
        (_box(100, 160), ("999", 0.8)),
        (_box(100, 180), ("138", 0.95)),
    ]
    toks = parse_tokens(lines)
    vals = sorted(t.value for t in toks)
    assert vals == [138]


def test_parse_tokens_multiple_numbers_in_one_line():
    lines = [(_box(100, 100), ("138/91", 0.9))]
    toks = parse_tokens(lines)
    assert sorted(t.value for t in toks) == [91, 138]


def test_extract_typical_bp_reading():
    tokens = [
        NumberToken(138, y=300, x=500, confidence=0.95, raw="138"),
        NumberToken(91, y=450, x=500, confidence=0.93, raw="91"),
        NumberToken(102, y=600, x=500, confidence=0.9, raw="102"),
    ]
    fields, cands = extract_fields(tokens)
    assert fields.systolic == 138
    assert fields.diastolic == 91
    assert fields.heart_rate == 102
    assert [c.label for c in cands] == ["systolic", "diastolic", "heart_rate"]


def test_extract_skips_noise_numbers_by_y_order():
    tokens = [
        NumberToken(2026, y=100, x=10, confidence=0.9, raw="2026"),  # filtered by value filter, shouldn't appear
        NumberToken(138, y=300, x=500, confidence=0.95, raw="138"),
        NumberToken(91, y=450, x=500, confidence=0.93, raw="91"),
        NumberToken(76, y=600, x=500, confidence=0.92, raw="76"),
    ]
    fields, _ = extract_fields(tokens)
    assert fields.systolic == 138
    assert fields.diastolic == 91
    assert fields.heart_rate == 76


def test_extract_returns_none_when_sys_le_dia():
    tokens = [
        NumberToken(80, y=300, x=500, confidence=0.9, raw="80"),
        NumberToken(120, y=450, x=500, confidence=0.9, raw="120"),
    ]
    fields, cands = extract_fields(tokens)
    assert fields.systolic == 80
    assert fields.diastolic is None
    assert not any(c.label == "diastolic" for c in cands)


def test_extract_partial_only_systolic():
    tokens = [NumberToken(118, y=300, x=500, confidence=0.8, raw="118")]
    fields, _ = extract_fields(tokens)
    assert fields.systolic == 118
    assert fields.diastolic is None
    assert fields.heart_rate is None


def test_extract_uses_y_order_not_magnitude():
    tokens = [
        NumberToken(89, y=300, x=500, confidence=0.9, raw="89"),
        NumberToken(52, y=450, x=500, confidence=0.9, raw="52"),
        NumberToken(89, y=600, x=500, confidence=0.9, raw="89"),
    ]
    fields, _ = extract_fields(tokens)
    assert fields.systolic == 89
    assert fields.diastolic == 52
    assert fields.heart_rate == 89
