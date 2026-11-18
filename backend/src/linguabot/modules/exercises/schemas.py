"""Pydantic-схемы грамматических упражнений."""

from pydantic import BaseModel


class OptionRead(BaseModel):
    id: int
    text: str


class ExerciseRead(BaseModel):
    id: int
    difficulty: str
    level_source: str
    topic: str
    prompt: str
    options: list[OptionRead]


class SubmitAnswerRequest(BaseModel):
    option_id: int


class AnswerFeedback(BaseModel):
    exercise_id: int
    difficulty: str
    selected_option_id: int
    correct: bool
    correct_option_id: int
    correct_text: str
    explanation: str
