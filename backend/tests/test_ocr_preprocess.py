import numpy as np

from app.services.ocr.preprocess import MAX_SIDE, decode, preprocess, preprocess_bytes


def _png_bytes(w: int = 40, h: int = 30) -> bytes:
    import cv2
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def test_decode_valid_png():
    img = decode(_png_bytes())
    assert img.shape == (30, 40, 3)


def test_decode_invalid_raises():
    import pytest
    with pytest.raises(ValueError):
        decode(b"not-an-image")


def test_preprocess_upscales_small_image_to_max_side():
    import cv2
    img = np.full((200, 150, 3), 128, dtype=np.uint8)
    out = preprocess(img)
    assert max(out.shape[:2]) == MAX_SIDE
    assert out.shape[2] == 3


def test_preprocess_bytes_roundtrip():
    out = preprocess_bytes(_png_bytes(200, 100))
    assert out.ndim == 3
    assert max(out.shape[:2]) == MAX_SIDE
