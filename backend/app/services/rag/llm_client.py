from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

import requests
from diskcache import Cache

from app.core.config import get_settings


class LLMError(Exception):
    pass


@dataclass
class ChatMessage:
    role: str
    content: str


def _cache() -> Cache:
    s = get_settings()
    Path(s.llm_cache_dir).mkdir(parents=True, exist_ok=True)
    return Cache(s.llm_cache_dir)


def _embed_cache_key(model: str, text: str) -> str:
    h = hashlib.sha256(f"{model}\x00{text}".encode("utf-8")).hexdigest()
    return f"emb:{h}"


def _chat_cache_key(model: str, messages: list[dict], temperature: float) -> str:
    payload = json.dumps(
        {"m": model, "msgs": messages, "t": temperature}, ensure_ascii=False, sort_keys=True
    )
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"chat:{h}"


def embed(texts: list[str], *, use_cache: bool = True) -> list[list[float]]:
    """Batch-embed using DashScope OpenAI-compatible endpoint.

    Returns one vector per input text. Raises LLMError on any failure.
    """
    if not texts:
        return []
    s = get_settings()
    if not s.dashscope_api_key:
        raise LLMError("dashscope_api_key is not configured")

    cache = _cache() if use_cache else None
    results: list[Optional[list[float]]] = [None] * len(texts)
    to_fetch: list[tuple[int, str]] = []

    for i, t in enumerate(texts):
        if cache is not None:
            v = cache.get(_embed_cache_key(s.dashscope_embedding_model, t))
            if v is not None:
                results[i] = v
                continue
        to_fetch.append((i, t))

    if to_fetch:
        # DashScope embedding API has batch size limit of 10
        batch_size = 10
        for batch_start in range(0, len(to_fetch), batch_size):
            batch = to_fetch[batch_start : batch_start + batch_size]
            resp = requests.post(
                s.dashscope_embedding_endpoint,
                headers={
                    "Authorization": f"Bearer {s.dashscope_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": s.dashscope_embedding_model,
                    "input": [t for _, t in batch],
                    "dimensions": s.dashscope_embedding_dim,
                    "encoding_format": "float",
                },
                timeout=s.dashscope_timeout,
            )
            if resp.status_code != 200:
                raise LLMError(f"embedding http {resp.status_code}: {resp.text[:200]}")
            data = resp.json().get("data", [])
            if len(data) != len(batch):
                raise LLMError(f"embedding count mismatch: got {len(data)}, want {len(batch)}")
            for (idx, text), item in zip(batch, data):
                vec = item.get("embedding")
                if not isinstance(vec, list):
                    raise LLMError("embedding response missing vector")
                results[idx] = vec
                if cache is not None:
                    cache.set(_embed_cache_key(s.dashscope_embedding_model, text), vec)

    out: list[list[float]] = []
    for v in results:
        assert v is not None
        out.append(v)
    return out


def chat(
    messages: Iterable[ChatMessage],
    *,
    temperature: Optional[float] = None,
    use_cache: bool = False,
) -> str:
    """Non-streaming chat. Primarily for tests / eval; production uses chat_stream."""
    s = get_settings()
    if not s.dashscope_api_key:
        raise LLMError("dashscope_api_key is not configured")
    msgs = [{"role": m.role, "content": m.content} for m in messages]
    temp = s.llm_temperature if temperature is None else temperature

    if use_cache:
        cache = _cache()
        key = _chat_cache_key(s.dashscope_chat_model, msgs, temp)
        hit = cache.get(key)
        if hit is not None:
            return hit

    resp = requests.post(
        s.dashscope_chat_endpoint,
        headers={
            "Authorization": f"Bearer {s.dashscope_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": s.dashscope_chat_model,
            "messages": msgs,
            "temperature": temp,
            "stream": False,
        },
        timeout=s.dashscope_timeout,
    )
    if resp.status_code != 200:
        raise LLMError(f"chat http {resp.status_code}: {resp.text[:200]}")
    body = resp.json()
    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"chat response malformed: {e}")
    if use_cache:
        _cache().set(_chat_cache_key(s.dashscope_chat_model, msgs, temp), text)
    return text


def chat_stream(
    messages: Iterable[ChatMessage],
    *,
    temperature: Optional[float] = None,
) -> Iterator[str]:
    """Yield content deltas as they arrive (SSE). Caller is responsible for assembly."""
    s = get_settings()
    if not s.dashscope_api_key:
        raise LLMError("dashscope_api_key is not configured")
    msgs = [{"role": m.role, "content": m.content} for m in messages]
    temp = s.llm_temperature if temperature is None else temperature

    with requests.post(
        s.dashscope_chat_endpoint,
        headers={
            "Authorization": f"Bearer {s.dashscope_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": s.dashscope_chat_model,
            "messages": msgs,
            "temperature": temp,
            "stream": True,
        },
        timeout=s.dashscope_timeout,
        stream=True,
    ) as resp:
        if resp.status_code != 200:
            raise LLMError(f"chat_stream http {resp.status_code}: {resp.text[:200]}")
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            if not raw.startswith("data:"):
                continue
            payload = raw[5:].strip()
            if payload == "[DONE]":
                break
            try:
                evt = json.loads(payload)
                delta = evt["choices"][0]["delta"].get("content") or ""
            except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                continue
            if delta:
                yield delta
