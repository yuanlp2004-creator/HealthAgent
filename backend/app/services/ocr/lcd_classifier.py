"""Lightweight local LCD screen classifier (HOG + SVM).

Replaces the VLM-based classify_lcd() with sub-millisecond local inference.
Model trained on 10 LCD + 10 non-LCD BP monitor images.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import cv2
import numpy as np

_MODEL_PATH = Path(__file__).resolve().parent / "lcd_classifier.pkl"
_bundle = None


def _get_bundle() -> dict:
    global _bundle
    if _bundle is None:
        with open(_MODEL_PATH, "rb") as f:
            _bundle = pickle.load(f)
    return _bundle


def _extract_features(img_bgr: np.ndarray) -> np.ndarray:
    bundle = _get_bundle()
    img_size = bundle["img_size"]
    img = cv2.resize(img_bgr, img_size)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hog = cv2.HOGDescriptor(
        _winSize=(128, 128),
        _blockSize=(16, 16),
        _blockStride=(8, 8),
        _cellSize=(8, 8),
        _nbins=9,
    )
    hog_feat = hog.compute(gray).flatten()

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    color_feat = []
    for ch in cv2.split(img):
        color_feat.extend([np.mean(ch), np.std(ch)])
    for ch in cv2.split(hsv):
        color_feat.extend([np.mean(ch), np.std(ch)])

    gray_flat = gray.flatten()
    brightness_feat = [
        np.percentile(gray_flat, 10),
        np.percentile(gray_flat, 50),
        np.percentile(gray_flat, 90),
        np.mean(gray),
    ]

    return np.concatenate([hog_feat, np.array(color_feat), np.array(brightness_feat)])


def classify_lcd(image_bytes: bytes) -> bool:
    """Classify whether image is a seven-segment LCD BP monitor screen.

    Returns True if LCD, False otherwise.
    If model file is missing, returns False (fall through to OCR path).
    """
    if not _MODEL_PATH.exists():
        return False

    try:
        bundle = _get_bundle()
        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return False
        feat = _extract_features(img).reshape(1, -1)
        X = bundle["scaler"].transform(feat)
        prob = bundle["model"].predict_proba(X)[0, 1]
        return prob > 0.5
    except Exception:
        return False
