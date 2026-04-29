from __future__ import annotations

import json
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import session as db_session
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import (
    AskRequest,
    ChatMessageOut,
    CitationOut,
    ConversationCreate,
    ConversationListOut,
    ConversationOut,
    MessageListOut,
)
from app.services import chat_store
from app.services.chat_store import ConversationNotFoundError
from app.services.rag import chat_service
from app.services.rag.retriever import RetrievedCitation

router = APIRouter(prefix="/chat", tags=["chat"])


def _serialize_message(msg) -> ChatMessageOut:
    cits = [CitationOut(**c) for c in chat_store.parse_citations(msg)]
    return ChatMessageOut(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        citations=cits,
        created_at=msg.created_at,
    )


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: ConversationCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = chat_store.create_conversation(db, current.id, payload.title)
    return ConversationOut.model_validate(conv)


@router.get("/conversations", response_model=ConversationListOut)
def list_conversations(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = chat_store.list_conversations(db, current.id)
    return ConversationListOut(items=[ConversationOut.model_validate(c) for c in items])


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conv_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        chat_store.delete_conversation(db, current.id, conv_id)
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return None


@router.get("/conversations/{conv_id}/messages", response_model=MessageListOut)
def list_messages(
    conv_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        msgs = chat_store.list_messages(db, current.id, conv_id)
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return MessageListOut(items=[_serialize_message(m) for m in msgs])


def _sse(event: str, data) -> str:
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)
    # "data:" lines may not contain embedded newlines unsplit per SSE spec
    lines = data.split("\n")
    body = "\n".join(f"data: {line}" for line in lines)
    return f"event: {event}\n{body}\n\n"


def _citation_payload(c: RetrievedCitation) -> dict:
    return {
        "idx": c.idx,
        "doc_id": c.doc_id,
        "title": c.title,
        "source": c.source,
        "url": c.url,
        "heading_path": c.heading_path,
        "text": c.text,
    }


@router.post("/conversations/{conv_id}/ask")
def ask(
    conv_id: int,
    payload: AskRequest,
    current: User = Depends(get_current_user),
):
    # Own DB session — we must keep it alive for the whole stream, so we do
    # NOT use the request-scoped get_db dependency here.
    db: Session = db_session.SessionLocal()
    try:
        try:
            conv = chat_store.get_conversation(db, current.id, conv_id)
        except ConversationNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

        chat_store.append_user_message(db, conv, payload.question)
        history = chat_store.load_history_as_chat_messages(db, conv.id)
        # drop the latest user msg from history because we'll rebuild it via build_user_message
        history = history[:-1] if history and history[-1].role == "user" else history
    except Exception:
        db.close()
        raise

    def event_generator() -> Iterator[bytes]:
        try:
            stream, citations = chat_service.answer_stream(
                db, current.id, payload.question, history=history
            )
            yield _sse("citations", [_citation_payload(c) for c in citations]).encode("utf-8")

            full: list[str] = []
            for delta in stream:
                full.append(delta)
                yield _sse("delta", delta).encode("utf-8")

            content = "".join(full)
            saved = chat_store.append_assistant_message(db, conv, content, citations)
            yield _sse("done", {"message_id": saved.id}).encode("utf-8")
        except Exception as e:
            logger.exception("sse ask failed: {}", e)
            yield _sse("error", {"detail": str(e)}).encode("utf-8")
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
