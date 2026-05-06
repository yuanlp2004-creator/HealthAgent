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

_CLASSIFY_PROMPT = (
    "判断这张图片是否属于七段数码管LCD电子血压计屏幕照片。\n"
    "七段数码管LCD的特征：深色背景（深绿/深灰/黑色），数字由分段的笔划组成"
    "（类似电子表或计算器显示），数字边缘可能有间隙，通常能看到SYS/DIA/PUL标签。\n"
    "非LCD的例子：智能手机App界面截图、电脑网页看板、打印的纸质标签、"
    "平板电脑测量结果页面。\n\n"
    "严格要求：\n"
    "1. 只返回严格的 JSON：{\"lcd\": true} 或 {\"lcd\": false}\n"
    "2. 不要任何解释、markdown、代码块标记。\n"
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


def _call_vlm(image_bytes: bytes, prompt: str) -> str:
    """Send image + prompt to Qwen-VL, return raw text content."""
    s = get_settings()
    b64 = base64.b64encode(image_bytes).decode("ascii")
    url = f"data:image/jpeg;base64,{b64}"
    payload = {
        "model": s.dashscope_vl_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": url}},
                    {"type": "text", "text": prompt},
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
        raise QwenVLError(f"http {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise QwenVLError(f"unexpected response: {data}")
    if isinstance(content, list):
        content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
    return content or ""


def classify_lcd(image_bytes: bytes) -> bool:
    """Classify whether image is a seven-segment LCD BP monitor screen."""
    s = get_settings()
    if not s.dashscope_api_key:
        return False  # can't classify, fall through to OCR
    try:
        content = _call_vlm(image_bytes, _CLASSIFY_PROMPT)
        parsed = _extract_json(content)
        if parsed and isinstance(parsed.get("lcd"), bool):
            return parsed["lcd"]
    except Exception:
        pass
    return False


def recognize_bp(image_bytes: bytes) -> dict:
    s = get_settings()
    if not s.dashscope_api_key:
        raise QwenVLError("DASHSCOPE_API_KEY not configured")
    try:
        content = _call_vlm(image_bytes, _PROMPT)
    except Exception as e:
        logger.warning("qwen-vl http error: {}", e)
        raise

    parsed = _extract_json(content)
    if parsed is None:
        logger.warning("qwen-vl cannot parse JSON from: {!r}", content)
        return {"systolic": None, "diastolic": None, "heart_rate": None}
    return {
        "systolic": _coerce_int(parsed.get("systolic")),
        "diastolic": _coerce_int(parsed.get("diastolic")),
        "heart_rate": _coerce_int(parsed.get("heart_rate")),
    }
