"""Бизнес-логика грамматических упражнений."""

from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.modules.assessment.repository import TestResultRepository
from linguabot.modules.exercises.questions import (
    EXERCISES,
    EXERCISES_BY_ID,
)
from linguabot.modules.exercises.schemas import (
    AnswerFeedback,
    ExerciseRead,
    OptionRead,
)
from linguabot.modules.users.models import User

DEFAULT_DIFFICULTY = "beginner"

LEVEL_TO_DIFFICULTY: dict[str, str] = {
    "beginner": "beginner",
    "intermediate": "intermediate",
    "advanced": "advanced",
}


class ExerciseNotFoundError(Exception):
    """Упражнение с указанным ID отсутствует."""


class InvalidOptionError(Exception):
    """Выбранный вариант не принадлежит упражнению."""


def difficulty_from_level(level: str | None) -> str:
    if level in LEVEL_TO_DIFFICULTY:
        return LEVEL_TO_DIFFICULTY[level]
    return DEFAULT_DIFFICULTY


async def resolve_difficulty(
    session: AsyncSession, user: User
) -> tuple[str, str]:
    latest = await TestResultRepository(session).get_latest_by_user(user.id)
    if latest is None:
        return DEFAULT_DIFFICULTY, "default"
    return difficulty_from_level(latest.level), "test"


def get_next_exercise(difficulty: str, exclude: set[int]) -> dict | None:
    items = EXERCISES.get(difficulty, [])
    for exercise in items:
        if exercise["id"] not in exclude:
            return exercise
    return items[0] if items else None


async def next_exercise(
    session: AsyncSession, user: User, exclude: set[int]
) -> ExerciseRead:
    difficulty, source = await resolve_difficulty(session, user)
    exercise = get_next_exercise(difficulty, exclude)
    if exercise is None:
        raise ExerciseNotFoundError
    return ExerciseRead(
        id=exercise["id"],
        difficulty=difficulty,
        level_source=source,
        topic=exercise["topic"],
        prompt=exercise["prompt"],
        options=[OptionRead(**option) for option in exercise["options"]],
    )


def check_answer(exercise_id: int, option_id: int) -> AnswerFeedback:
    exercise = EXERCISES_BY_ID.get(exercise_id)
    if exercise is None:
        raise ExerciseNotFoundError
    option_ids = {option["id"] for option in exercise["options"]}
    if option_id not in option_ids:
        raise InvalidOptionError
    correct_option_id = exercise["correct_option_id"]
    correct_option = next(
        option
        for option in exercise["options"]
        if option["id"] == correct_option_id
    )
    return AnswerFeedback(
        exercise_id=exercise_id,
        difficulty=exercise["difficulty"],
        selected_option_id=option_id,
        correct=option_id == correct_option_id,
        correct_option_id=correct_option_id,
        correct_text=correct_option["text"],
        explanation=exercise["explanation"],
    )
