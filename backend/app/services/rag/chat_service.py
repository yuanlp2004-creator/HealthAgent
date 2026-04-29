from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.rag import llm_client
from app.services.rag.llm_client import ChatMessage
from app.services.rag.prompt import (
    SYSTEM_PROMPT,
    UserHealthContext,
    build_user_context,
    build_user_message,
)
from app.services.rag.retriever import RetrievedCitation, retrieve


@dataclass
class RagAnswer:
    content: str
    citations: list[RetrievedCitation]


def _prepare(
    db: Session,
    user_id: int,
    question: str,
    *,
    history: Optional[list[ChatMessage]] = None,
) -> tuple[list[ChatMessage], list[RetrievedCitation]]:
    s = get_settings()
    citations = retrieve(question, top_k=s.rag_top_k)
    context = build_user_context(db, user_id, days=14)
    user_msg = build_user_message(question, citations, context)

    msgs: list[ChatMessage] = [ChatMessage(role="system", content=SYSTEM_PROMPT)]
    if history:
        # trim to the last 6 turns to keep prompt bounded
        msgs.extend(history[-12:])
    msgs.append(ChatMessage(role="user", content=user_msg))
    return msgs, citations


def answer(
    db: Session,
    user_id: int,
    question: str,
    *,
    history: Optional[list[ChatMessage]] = None,
) -> RagAnswer:
    """Blocking answer — used for evaluation and tests."""
    msgs, citations = _prepare(db, user_id, question, history=history)
    content = llm_client.chat(msgs)
    return RagAnswer(content=content, citations=citations)


def answer_stream(
    db: Session,
    user_id: int,
    question: str,
    *,
    history: Optional[list[ChatMessage]] = None,
) -> tuple[Iterator[str], list[RetrievedCitation]]:
    """Return (delta iterator, citations). Citations are known immediately;
    content streams in as the LLM emits deltas."""
    msgs, citations = _prepare(db, user_id, question, history=history)
    stream = llm_client.chat_stream(msgs)
    return stream, citations
