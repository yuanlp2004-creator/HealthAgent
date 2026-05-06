"""
Dual-mode OCR benchmark: compare Baidu OCR primary path vs VLM fallback.
Usage:
  python ocr_bench_dual.py             # both datasets, both modes
  python ocr_bench_dual.py --ocr-only  # disable VLM fallback
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import ocr_service  # noqa: E402


DATASETS = {
    "lcd": "datasets/bp_images",
    "clean": "datasets/bp_clean",
}


def run_benchmark(dataset_path, disable_vlm=False):
    """Run OCR benchmark. If disable_vlm=True, monkey-patch to skip VLM fallback."""
    labels_path = dataset_path / "labels.json"
    if not labels_path.exists():
        print(f"  labels.json not found at {labels_path}")
        return None

    labels = json.loads(labels_path.read_text(encoding="utf-8"))

    # Monkey-patch to disable VLM
    original = ocr_service._apply_vlm_fallback
    if disable_vlm:
        def no_vlm(result, _img_bytes):
            return result
        ocr_service._apply_vlm_fallback = no_vlm

    try:
        total = len(labels) * 3
        hits = 0
        per_field = {"systolic": [0, 0], "diastolic": [0, 0], "heart_rate": [0, 0]}
        rows = []
        total_elapsed = 0.0
        vlm_calls = 0

        for item in labels:
            img_path = dataset_path / item["file"]
            if not img_path.exists():
                print(f"    [SKIP] Missing: {item['file']}")
                continue
            data = img_path.read_bytes()
            t0 = time.perf_counter()
            res = ocr_service.recognize(data)
            elapsed = time.perf_counter() - t0
            total_elapsed += elapsed
            pred = res.fields.to_dict()

            # Check if VLM was used (fields were filled after being empty)
            # In no-vlm mode, incomplete fields stay as None
            has_vlm = not disable_vlm and pred.get("systolic") is not None

            row = {
                "file": item["file"],
                "elapsed_s": round(elapsed, 2),
                "pred": pred,
                "truth": {k: item[k] for k in ("systolic", "diastolic", "heart_rate")},
            }
            for f in ("systolic", "diastolic", "heart_rate"):
                per_field[f][1] += 1
                if pred.get(f) == item[f]:
                    per_field[f][0] += 1
                    hits += 1
            rows.append(row)

        return {
            "samples": len(rows),
            "total_fields": total,
            "hits": hits,
            "accuracy": hits / total * 100 if total > 0 else 0,
            "avg_elapsed": total_elapsed / len(rows) if rows else 0,
            "per_field": per_field,
            "rows": rows,
        }
    finally:
        ocr_service._apply_vlm_fallback = original


def print_results(results, label):
    if results is None:
        return
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Samples: {results['samples']}  |  Fields: {results['total_fields']}")
    print(f"  Overall: {results['hits']}/{results['total_fields']} ({results['accuracy']:.1f}%)")
    print(f"  Average elapsed: {results['avg_elapsed']:.2f}s")
    print(f"  Per-field:")
    for k, (ok, n) in results["per_field"].items():
        print(f"    {k:12s}  {ok}/{n}  ({ok / n * 100:.1f}%)")
    print(f"\n  Per-sample:")
    for r in results["rows"]:
        match = all(r["pred"].get(k) == r["truth"][k] for k in ("systolic", "diastolic", "heart_rate"))
        flag = "OK" if match else "XX"
        print(f"    {flag} {r['file']}: pred={r['pred']} truth={r['truth']} ({r['elapsed_s']:.2f}s)")


def main():
    disable_only = "--ocr-only" in sys.argv
    modes = [(True, "OCR-Only (VLM disabled)")]
    if not disable_only:
        modes.append((False, "Full Pipeline (Baidu + VLM)"))

    for disable_vlm, mode_name in modes:
        for ds_name, ds_rel_path in DATASETS.items():
            ds_path = (ROOT.parent / ds_rel_path).resolve()
            label = f"[{ds_name.upper()}] {mode_name}"
            results = run_benchmark(ds_path, disable_vlm=disable_vlm)
            print_results(results, label)

    print()


if __name__ == "__main__":
    raise SystemExit(main())
