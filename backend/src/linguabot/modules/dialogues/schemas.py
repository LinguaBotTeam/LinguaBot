"""Форматы запросов и ответов текстового чата."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DialogueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(default="Новый диалог", min_length=1, max_length=160)
    scenario: str = Field(default="free_chat", min_length=1, max_length=64)


class DialogueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    scenario: str
    status: Literal["active", "completed"]
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=4000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dialogue_id: int
    role: Literal["user", "assistant"]
    content: str
    correction: str | None
    created_at: datetime


class MessagePair(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead
