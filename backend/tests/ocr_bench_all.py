"""
Benchmark ALL 5 OCR schemes on the full 10-image LCD dataset.
Schemes:
  1. PaddleOCR PP-OCRv4 (original image only, no CLAHE variants)
  2. PaddleOCR + CLAHE/逆变体 (3 preprocessed variants)
  3. Baidu accurate 通用OCR
  4. Baidu numbers 数字OCR + bbox过滤
  5. Baidu numbers + VLM兜底 (完整管线)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.ocr.extractor import extract_fields, parse_tokens
from app.services.ocr.preprocess import decode, preprocess_bytes_variants
from app.services.ocr.baidu_client import recognize_accurate, recognize_numbers
from app.services import ocr_service


DATASET_PATH = ROOT.parent / "datasets" / "bp_images"
LABELS_PATH = DATASET_PATH / "labels.json"


def run_paddle_original(image_bytes):
    """Scheme 1: PaddleOCR on original image only."""
    from paddleocr import PaddleOCR
    engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    img = decode(image_bytes)
    raw = engine.ocr(img, cls=True)
    lines = raw[0] if raw and raw[0] else []
    tokens = parse_tokens(lines)
    fields, _ = extract_fields(tokens)
    return fields


def run_paddle_clahe_variants(image_bytes):
    """Scheme 2: PaddleOCR on 3 preprocessed variants (original + CLAHE + inverted)."""
    from paddleocr import PaddleOCR
    engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    all_tokens = []
    for variant in preprocess_bytes_variants(image_bytes):
        raw = engine.ocr(variant, cls=True)
        lines = raw[0] if raw and raw[0] else []
        all_tokens.extend(parse_tokens(lines))
    # Deduplicate
    dedup = []
    for t in all_tokens:
        merged = False
        for d in dedup:
            if d.value == t.value and abs(d.y - t.y) < 40 and abs(d.x - t.x) < 80:
                if t.confidence > d.confidence:
                    d.confidence = t.confidence
                merged = True
                break
        if not merged:
            dedup.append(t)
    fields, _ = extract_fields(dedup)
    return fields


def run_baidu_accurate(image_bytes):
    """Scheme 3: Baidu accurate general OCR."""
    words = recognize_accurate(image_bytes)
    for w in words:
        w.setdefault("probability", {"average": 0.99})
    from app.services.ocr_service import _baidu_lines_to_ocr_lines
    lines = _baidu_lines_to_ocr_lines(words)
    tokens = parse_tokens(lines)
    fields, _ = extract_fields(tokens)
    return fields


def run_baidu_numbers(image_bytes):
    """Scheme 4: Baidu numbers OCR with bbox filtering."""
    words = recognize_numbers(image_bytes)
    for w in words:
        w.setdefault("probability", {"average": 0.99})
    from app.services.ocr_service import _baidu_lines_to_ocr_lines
    lines = _baidu_lines_to_ocr_lines(words)
    tokens = parse_tokens(lines)
    fields, _ = extract_fields(tokens)
    return fields


def run_full_pipeline(image_bytes):
    """Scheme 5: Full pipeline (Baidu numbers + VLM fallback)."""
    res = ocr_service.recognize(image_bytes)
    return res.fields


SCHEMES = [
    ("PaddleOCR PP-OCRv4（CPU，通用中英）", run_paddle_original),
    ("PaddleOCR + CLAHE/反色三变体", run_paddle_clahe_variants),
    ("百度云 accurate 通用OCR", run_baidu_accurate),
    ("百度云 numbers数字OCR + bbox过滤", run_baidu_numbers),
    ("百度云主通路 + VLM兜底（本文方案）", run_full_pipeline),
]


def main():
    labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    # Only real LCD images
    lcd_items = [item for item in labels if item.get("source") == "real"]

    img_files = []
    for item in lcd_items:
        img_path = DATASET_PATH / item["file"]
        if img_path.exists():
            img_files.append((item, img_path.read_bytes()))

    total_fields = len(img_files) * 3
    print(f"Dataset: {len(img_files)} images, {total_fields} fields\n")

    results_table = []

    for scheme_name, scheme_fn in SCHEMES:
        hits = 0
        total_elapsed = 0.0
        per_field = {"systolic": [0, 0], "diastolic": [0, 0], "heart_rate": [0, 0]}
        per_sample = []

        for item, img_data in img_files:
            t0 = time.perf_counter()
            try:
                fields = scheme_fn(img_data)
            except Exception as e:
                fields = type('F', (), {'to_dict': lambda: {"systolic": None, "diastolic": None, "heart_rate": None}})()
                print(f"    [ERR] {scheme_name} on {item['file']}: {e}")
            elapsed = time.perf_counter() - t0
            total_elapsed += elapsed
            pred = fields.to_dict() if hasattr(fields, 'to_dict') else {"systolic": None, "diastolic": None, "heart_rate": None}

            sample_hits = 0
            for f in ("systolic", "diastolic", "heart_rate"):
                per_field[f][1] += 1
                if pred.get(f) == item[f]:
                    per_field[f][0] += 1
                    hits += 1
                    sample_hits += 1
            per_sample.append((item["file"], pred, sample_hits, elapsed))

        accuracy = hits / total_fields * 100 if total_fields > 0 else 0
        avg_elapsed = total_elapsed / len(img_files) if img_files else 0
        results_table.append((scheme_name, accuracy, avg_elapsed, per_field, per_sample))

        print(f"{'='*60}")
        print(f"  {scheme_name}")
        print(f"  Overall: {hits}/{total_fields} ({accuracy:.1f}%)  |  Avg: {avg_elapsed:.2f}s")
        for f, (ok, n) in per_field.items():
            print(f"    {f:12s}: {ok}/{n}  ({ok/n*100:.1f}%)")
        print(f"  Per-sample:")
        for fname, pred, sh, el in per_sample:
            flag = "OK" if sh == 3 else f"{sh}/3"
            print(f"    [{flag}] {fname}: {pred} ({el:.2f}s)")

    # Summary table
    print(f"\n{'='*70}")
    print(f"  SUMMARY TABLE")
    print(f"{'='*70}")
    print(f"  {'Scheme':<44s} {'Accuracy':>10s} {'Time':>8s}")
    print(f"  {'-'*62}")
    for scheme_name, accuracy, avg_elapsed, _, _ in results_table:
        bold = "**" if "VLM" in scheme_name else "  "
        print(f"  {bold}{scheme_name:<42s}{bold} {accuracy:>7.1f}% {avg_elapsed:>6.2f}s")
    print()


if __name__ == "__main__":
    raise SystemExit(main())
