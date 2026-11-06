"""Бизнес-логика теста уровня."""

from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.modules.assessment.models import TestResult
from linguabot.modules.assessment.questions import (
    ENGLISH_QUESTIONS,
    QUESTION_COUNT,
    QUESTIONS_BY_ID,
)
from linguabot.modules.assessment.repository import TestResultRepository
from linguabot.modules.assessment.schemas import (
    QuestionRead,
    QuestionsResponse,
    SubmitTestRequest,
)
from linguabot.modules.users.models import User

TEST_LANGUAGE = "en"

# Пороги уровня: score → (level, cefr).
LEVEL_THRESHOLDS: list[tuple[int, str, str]] = [
    (20, "beginner", "A1"),
    (40, "beginner", "A2"),
    (60, "intermediate", "B1"),
    (80, "intermediate", "B2"),
]


class InvalidAnswersError(Exception):
    """Ответы не соответствуют банку вопросов."""


def get_questions() -> QuestionsResponse:
    return QuestionsResponse(
        language=TEST_LANGUAGE,
        questions=[
            QuestionRead(
                id=question["id"],
                text=question["text"],
                options=question["options"],
            )
            for question in ENGLISH_QUESTIONS
        ],
    )


def resolve_level(score: int) -> tuple[str, str]:
    for threshold, level, cefr in LEVEL_THRESHOLDS:
        if score <= threshold:
            return level, cefr
    return "advanced", "C1"


async def submit_test(
    session: AsyncSession, user: User, data: SubmitTestRequest
) -> TestResult:
    given: dict[int, int] = {}
    for answer in data.answers:
        question = QUESTIONS_BY_ID.get(answer.question_id)
        if question is None:
            raise InvalidAnswersError
        if answer.question_id in given:
            raise InvalidAnswersError
        option_ids = {option["id"] for option in question["options"]}
        if answer.option_id not in option_ids:
            raise InvalidAnswersError
        given[answer.question_id] = answer.option_id

    if set(given) != set(QUESTIONS_BY_ID):
        raise InvalidAnswersError

    question_results = []
    correct_count = 0
    for question in ENGLISH_QUESTIONS:
        is_correct = given[question["id"]] == question["correct_option_id"]
        correct_count += int(is_correct)
        question_results.append(
            {
                "question_id": question["id"],
                "correct": is_correct,
                "correct_option_id": question["correct_option_id"],
            }
        )

    score = round(correct_count * 100 / QUESTION_COUNT)
    level, cefr = resolve_level(score)

    return await TestResultRepository(session).create(
        user_id=user.id,
        score=score,
        level=level,
        cefr=cefr,
        details={"language": TEST_LANGUAGE, "questions": question_results},
    )


async def get_latest_result(
    session: AsyncSession, user: User
) -> TestResult | None:
    return await TestResultRepository(session).get_latest_by_user(user.id)
