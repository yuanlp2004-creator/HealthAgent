from __future__ import annotations

import base64
import json
import re
from typing import Optional

import requests
from loguru import logger

from app.core.config import get_settings

_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

_PROMPT = (
    "你将看到一张家用电子血压计的照片。请识别主显示屏上的三项大号数字：\n"
    "- systolic（收缩压，合理范围 60-250）\n"
    "- diastolic（舒张压，合理范围 30-160）\n"
    "- heart_rate（心率/脉搏，合理范围 30-200）\n\n"
    "**严格要求**：\n"
    "1. 只返回严格的 JSON，不要任何解释、markdown、代码块标记。\n"
    '2. 格式：{"systolic": <int|null>, "diastolic": <int|null>, "heart_rate": <int|null>}\n'
    "3. 如果图像模糊、反光严重、数字被遮挡或你无法完全确信某个字段的每一位数字，"
    "**对应字段必须返回 null**。\n"
    "4. **禁止**基于'正常血压一般是 120/80'之类的常识进行推测或填充。\n"
    "5. 只有当你能清楚看到数字的每一位笔画时才给出数值。\n\n"
    "反面示例（图像模糊时）：\n"
    '{"systolic": null, "diastolic": null, "heart_rate": null}\n\n'
    "反面示例（只看清高压时）：\n"
    '{"systolic": 138, "diastolic": null, "heart_rate": null}'
)


class QwenVLError(RuntimeError):
    pass


def _extract_json(text: str) -> Optional[dict]:
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _coerce_int(v) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if not s or s.lower() in ("null", "none", "n/a"):
            return None
        try:
            return int(float(s))
        except ValueError:
            return None
    return None


def recognize_bp(image_bytes: bytes) -> dict:
    s = get_settings()
    if not s.dashscope_api_key:
        raise QwenVLError("DASHSCOPE_API_KEY not configured")
    b64 = base64.b64encode(image_bytes).decode("ascii")
    url = f"data:image/jpeg;base64,{b64}"
    payload = {
        "model": s.dashscope_vl_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": url}},
                    {"type": "text", "text": _PROMPT},
                ],
            }
        ],
        "temperature": 0.0,
    }
    resp = requests.post(
        _ENDPOINT,
        headers={
            "Authorization": f"Bearer {s.dashscope_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=s.dashscope_timeout,
    )
    if resp.status_code >= 400:
        logger.warning("qwen-vl http {}: {}", resp.status_code, resp.text[:500])
        raise QwenVLError(f"http {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise QwenVLError(f"unexpected response: {data}")

    if isinstance(content, list):
        content = "".join(c.get("text", "") for c in content if isinstance(c, dict))

    parsed = _extract_json(content or "")
    if parsed is None:
        logger.warning("qwen-vl cannot parse JSON from: {!r}", content)
        return {"systolic": None, "diastolic": None, "heart_rate": None}
    return {
        "systolic": _coerce_int(parsed.get("systolic")),
        "diastolic": _coerce_int(parsed.get("diastolic")),
        "heart_rate": _coerce_int(parsed.get("heart_rate")),
    }
