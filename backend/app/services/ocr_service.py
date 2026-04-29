from __future__ import annotations

import threading

from loguru import logger

from app.core.config import get_settings
from app.services.ocr.extractor import (
    FieldCandidate,
    NumberToken,
    OCRFields,
    OCRResult,
    extract_fields,
    parse_tokens,
)
from app.services.ocr.preprocess import preprocess_bytes_variants

_ocr_engine = None
_lock = threading.Lock()


def _get_paddle_engine():
    global _ocr_engine
    if _ocr_engine is None:
        with _lock:
            if _ocr_engine is None:
                from paddleocr import PaddleOCR
                logger.info("loading PaddleOCR PP-OCRv4 (ch)...")
                _ocr_engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    return _ocr_engine


def _dedup_tokens(tokens: list[NumberToken]) -> list[NumberToken]:
    out: list[NumberToken] = []
    for t in tokens:
        merged = False
        for o in out:
            if o.value == t.value and abs(o.y - t.y) < 40 and abs(o.x - t.x) < 80:
                if t.confidence > o.confidence:
                    o.confidence = t.confidence
                merged = True
                break
        if not merged:
            out.append(t)
    return out


def _recognize_paddle(image_bytes: bytes) -> tuple[str, list[NumberToken]]:
    engine = _get_paddle_engine()
    all_lines: list = []
    all_tokens: list[NumberToken] = []
    for variant in preprocess_bytes_variants(image_bytes):
        raw = engine.ocr(variant, cls=True)
        lines = raw[0] if raw and raw[0] else []
        all_lines.extend(lines)
        all_tokens.extend(parse_tokens(lines))
    raw_text = "\n".join(t for _, (t, _c) in all_lines)
    return raw_text, _dedup_tokens(all_tokens)


def _baidu_lines_to_ocr_lines(words: list[dict]) -> list:
    out = []
    for w in words:
        text = w.get("words", "")
        loc = w.get("location") or {}
        left = float(loc.get("left", 0))
        top = float(loc.get("top", 0))
        width = float(loc.get("width", 0))
        height = float(loc.get("height", 0))
        box = [
            [left, top],
            [left + width, top],
            [left + width, top + height],
            [left, top + height],
        ]
        prob = w.get("probability") or {}
        conf = float(prob.get("average", 0.99))
        out.append((box, (text, conf)))
    return out


def _recognize_baidu(image_bytes: bytes) -> tuple[str, list[NumberToken]]:
    from app.services.ocr.baidu_client import recognize_numbers
    words = recognize_numbers(image_bytes)
    for w in words:
        w.setdefault("probability", {"average": 0.99})
    lines = _baidu_lines_to_ocr_lines(words)
    raw_text = "\n".join(t for _, (t, _c) in lines)
    tokens = parse_tokens(lines)
    return raw_text, tokens


def _is_complete(fields: OCRFields) -> bool:
    return all(
        v is not None
        for v in (fields.systolic, fields.diastolic, fields.heart_rate)
    )


def _apply_vlm_fallback(result: OCRResult, image_bytes: bytes) -> OCRResult:
    s = get_settings()
    if not s.ocr_vlm_fallback or not s.dashscope_api_key:
        return result
    if _is_complete(result.fields):
        return result
    try:
        from app.services.ocr.qwen_vl_client import recognize_bp
        vlm = recognize_bp(image_bytes)
    except Exception as e:
        logger.warning("vlm fallback failed: {}", e)
        return result

    logger.info("vlm fallback result: {}", vlm)
    fields = OCRFields(
        systolic=vlm.get("systolic"),
        diastolic=vlm.get("diastolic"),
        heart_rate=vlm.get("heart_rate"),
    )
    if fields.systolic is not None and fields.diastolic is not None:
        if fields.systolic <= fields.diastolic:
            fields.diastolic = None

    cands: list[FieldCandidate] = [
        FieldCandidate(label="systolic", value=fields.systolic, confidence=0.99)
        for _ in [0] if fields.systolic is not None
    ] + [
        FieldCandidate(label="diastolic", value=fields.diastolic, confidence=0.99)
        for _ in [0] if fields.diastolic is not None
    ] + [
        FieldCandidate(label="heart_rate", value=fields.heart_rate, confidence=0.99)
        for _ in [0] if fields.heart_rate is not None
    ]
    return OCRResult(
        raw_text=result.raw_text + "\n[vlm]" + str(vlm),
        tokens=result.tokens,
        candidates=cands or result.candidates,
        fields=fields,
    )


def recognize(image_bytes: bytes) -> OCRResult:
    engine_name = get_settings().ocr_engine
    if engine_name == "paddle":
        raw_text, tokens = _recognize_paddle(image_bytes)
    elif engine_name == "baidu":
        raw_text, tokens = _recognize_baidu(image_bytes)
    else:
        raise ValueError(f"unknown OCR engine: {engine_name}")
    fields, candidates = extract_fields(tokens)
    result = OCRResult(raw_text=raw_text, tokens=tokens, candidates=candidates, fields=fields)
    return _apply_vlm_fallback(result, image_bytes)
