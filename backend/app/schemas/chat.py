from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListOut(BaseModel):
    items: list[ConversationOut]


class CitationOut(BaseModel):
    idx: int
    doc_id: str
    title: str
    source: str
    url: Optional[str] = None
    heading_path: str
    text: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    citations: list[CitationOut] = Field(default_factory=list)
    created_at: datetime


class MessageListOut(BaseModel):
    items: list[ChatMessageOut]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
