from __future__ import annotations

import cv2
import numpy as np

MAX_SIDE = 1920


def decode(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("cannot decode image")
    return img


def _resize(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    scale = MAX_SIDE / max(h, w)
    if scale > 1:
        return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    if scale < 1:
        return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img


def _clahe(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def preprocess(img: np.ndarray) -> np.ndarray:
    img = _resize(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = _clahe(gray)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def preprocess_variants(img: np.ndarray) -> list[np.ndarray]:
    img = _resize(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    v_clahe = _clahe(gray)
    v_inv = cv2.bitwise_not(v_clahe)
    return [
        img,
        cv2.cvtColor(v_clahe, cv2.COLOR_GRAY2BGR),
        cv2.cvtColor(v_inv, cv2.COLOR_GRAY2BGR),
    ]


def preprocess_bytes(image_bytes: bytes) -> np.ndarray:
    return preprocess(decode(image_bytes))


def preprocess_bytes_variants(image_bytes: bytes) -> list[np.ndarray]:
    return preprocess_variants(decode(image_bytes))
