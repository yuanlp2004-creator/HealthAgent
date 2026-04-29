from __future__ import annotations

import json
from dataclasses import asdict
from typing import Optional

from sqlalchemy.orm import Session

from app.models.conversation import ChatMessage as ChatMessageModel
from app.models.conversation import Conversation
from app.services.rag.retriever import RetrievedCitation


class ConversationNotFoundError(Exception):
    pass


def create_conversation(db: Session, user_id: int, title: Optional[str] = None) -> Conversation:
    conv = Conversation(user_id=user_id, title=title or "新对话")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def list_conversations(db: Session, user_id: int) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def get_conversation(db: Session, user_id: int, conv_id: int) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if conv is None or conv.user_id != user_id:
        raise ConversationNotFoundError(f"conversation {conv_id} not found")
    return conv


def delete_conversation(db: Session, user_id: int, conv_id: int) -> None:
    conv = get_conversation(db, user_id, conv_id)
    db.delete(conv)
    db.commit()


def list_messages(db: Session, user_id: int, conv_id: int) -> list[ChatMessageModel]:
    get_conversation(db, user_id, conv_id)  # authorize
    return (
        db.query(ChatMessageModel)
        .filter(ChatMessageModel.conversation_id == conv_id)
        .order_by(ChatMessageModel.id.asc())
        .all()
    )


def append_user_message(db: Session, conv: Conversation, content: str) -> ChatMessageModel:
    msg = ChatMessageModel(conversation_id=conv.id, role="user", content=content)
    db.add(msg)
    # touch updated_at
    conv.title = conv.title if conv.title and conv.title != "新对话" else _title_from(content)
    db.commit()
    db.refresh(msg)
    return msg


def append_assistant_message(
    db: Session,
    conv: Conversation,
    content: str,
    citations: list[RetrievedCitation],
) -> ChatMessageModel:
    payload = [
        {
            "idx": c.idx,
            "doc_id": c.doc_id,
            "title": c.title,
            "source": c.source,
            "url": c.url,
            "heading_path": c.heading_path,
            "text": c.text,
        }
        for c in citations
    ]
    msg = ChatMessageModel(
        conversation_id=conv.id,
        role="assistant",
        content=content,
        citations_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def _title_from(content: str) -> str:
    first_line = content.strip().splitlines()[0] if content.strip() else "新对话"
    return first_line[:30]


def parse_citations(msg: ChatMessageModel) -> list[dict]:
    if not msg.citations_json:
        return []
    try:
        data = json.loads(msg.citations_json)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return []


def load_history_as_chat_messages(
    db: Session, conv_id: int, *, limit_turns: int = 6
) -> list:
    """Return recent messages as list[ChatMessage] for LLM prompt (latest 'limit_turns'
    user+assistant pairs)."""
    from app.services.rag.llm_client import ChatMessage as LLMChatMessage

    recent = (
        db.query(ChatMessageModel)
        .filter(ChatMessageModel.conversation_id == conv_id)
        .order_by(ChatMessageModel.id.desc())
        .limit(limit_turns * 2)
        .all()
    )
    recent.reverse()
    return [LLMChatMessage(role=m.role, content=m.content) for m in recent]
