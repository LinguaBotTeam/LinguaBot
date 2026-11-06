"""Pydantic-схемы теста уровня."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OptionRead(BaseModel):
    id: int
    text: str


class QuestionRead(BaseModel):
    id: int
    text: str
    options: list[OptionRead]


class QuestionsResponse(BaseModel):
    language: str
    questions: list[QuestionRead]


class AnswerSubmit(BaseModel):
    question_id: int
    option_id: int


class SubmitTestRequest(BaseModel):
    answers: list[AnswerSubmit] = Field(min_length=1)


class QuestionResult(BaseModel):
    question_id: int
    correct: bool
    correct_option_id: int


class TestResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    score: int
    level: str
    cefr: str | None
    language: str
    questions: list[QuestionResult]
    taken_at: datetime

    @classmethod
    def from_model(cls, result: Any) -> "TestResultRead":
        details = result.details or {}
        return cls(
            id=result.id,
            score=result.score,
            level=result.level,
            cefr=result.cefr,
            language=details.get("language", "en"),
            questions=[QuestionResult(**item) for item in details.get("questions", [])],
            taken_at=result.taken_at,
        )
