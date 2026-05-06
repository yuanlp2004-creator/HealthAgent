"""OCR benchmark: run OCR pipeline over labeled samples and report field accuracy."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import ocr_service  # noqa: E402


def main() -> int:
    dataset = Path("datasets/bp_images")
    if not dataset.is_absolute():
        dataset = (ROOT.parent / dataset).resolve()
    labels_path = dataset / "labels.json"
    if not labels_path.exists():
        print(f"labels.json not found at {labels_path}")
        return 1
    labels = json.loads(labels_path.read_text(encoding="utf-8"))

    total = len(labels) * 3
    hits = 0
    per_field = {"systolic": [0, 0], "diastolic": [0, 0], "heart_rate": [0, 0]}
    rows = []
    total_elapsed = 0.0

    for item in labels:
        img_path = dataset / item["file"]
        if not img_path.exists():
            print(f"  [SKIP] Missing: {item['file']}")
            continue
        data = img_path.read_bytes()
        t0 = time.perf_counter()
        res = ocr_service.recognize(data)
        elapsed = time.perf_counter() - t0
        total_elapsed += elapsed
        pred = res.fields.to_dict()
        row = {"file": item["file"], "elapsed_s": round(elapsed, 2), "pred": pred, "truth": {k: item[k] for k in ("systolic", "diastolic", "heart_rate")}}
        for f in ("systolic", "diastolic", "heart_rate"):
            per_field[f][1] += 1
            if pred.get(f) == item[f]:
                per_field[f][0] += 1
                hits += 1
        rows.append(row)

    print("=== Per-sample ===")
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
    print()
    print("=== Per-field accuracy ===")
    for k, (ok, n) in per_field.items():
        print(f"  {k:10s}  {ok}/{n}  ({ok / n * 100:.1f}%)")
    print()
    print(f"Overall: {hits}/{total} ({hits / total * 100:.1f}%)")
    print(f"Average elapsed: {total_elapsed / len(labels):.2f}s  (samples={len(labels)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
