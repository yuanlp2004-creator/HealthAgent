from __future__ import annotations

import base64
import time
from threading import Lock
from typing import Any

import requests
from loguru import logger

from app.core.config import get_settings

_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_ACCURATE_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate"
_NUMBERS_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/numbers"

_cached_token: str | None = None
_cached_expire_at: float = 0.0
_lock = Lock()


class BaiduOCRError(RuntimeError):
    pass


def _get_access_token() -> str:
    global _cached_token, _cached_expire_at
    with _lock:
        now = time.time()
        if _cached_token and now < _cached_expire_at - 60:
            return _cached_token
        s = get_settings()
        if not s.baidu_ocr_ak or not s.baidu_ocr_sk:
            raise BaiduOCRError("baidu OCR AK/SK not configured")
        resp = requests.post(
            _TOKEN_URL,
            params={
                "grant_type": "client_credentials",
                "client_id": s.baidu_ocr_ak,
                "client_secret": s.baidu_ocr_sk,
            },
            timeout=s.baidu_ocr_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if "access_token" not in data:
            raise BaiduOCRError(f"token error: {data}")
        _cached_token = data["access_token"]
        _cached_expire_at = now + float(data.get("expires_in", 2592000))
        return _cached_token


def _call(url: str, payload: dict) -> dict:
    s = get_settings()
    token = _get_access_token()
    resp = requests.post(
        f"{url}?access_token={token}",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=s.baidu_ocr_timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error_code" in data:
        logger.warning("baidu OCR error: {}", data)
        raise BaiduOCRError(f"{data.get('error_code')}: {data.get('error_msg')}")
    return data


def recognize_accurate(image_bytes: bytes) -> list[dict[str, Any]]:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data = _call(_ACCURATE_URL, {"image": b64, "probability": "true"})
    return data.get("words_result", [])


def recognize_numbers(image_bytes: bytes) -> list[dict[str, Any]]:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data = _call(_NUMBERS_URL, {"image": b64})
    return data.get("words_result", [])


def recognize_combined(image_bytes: bytes) -> list[dict[str, Any]]:
    """Numbers API (for main LCD digits) + accurate fallback (for missed areas).
    Returns merged word list; numbers results keep no probability so default to 0.99."""
    out: list[dict[str, Any]] = []
    try:
        nums = recognize_numbers(image_bytes)
        for w in nums:
            w.setdefault("probability", {"average": 0.99})
        out.extend(nums)
    except BaiduOCRError as e:
        logger.warning("numbers API failed: {}", e)
    try:
        acc = recognize_accurate(image_bytes)
        out.extend(acc)
    except BaiduOCRError as e:
        logger.warning("accurate API failed: {}", e)
    return out
