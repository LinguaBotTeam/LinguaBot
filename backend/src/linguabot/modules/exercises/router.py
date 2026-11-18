"""Маршруты грамматических упражнений."""

from fastapi import APIRouter

from linguabot.core.errors import APIError
from linguabot.modules.auth.dependencies import CurrentUser, SessionDep
from linguabot.modules.exercises import service
from linguabot.modules.exercises.schemas import (
    AnswerFeedback,
    ExerciseRead,
    SubmitAnswerRequest,
)

router = APIRouter()


def parse_exclude(raw: str) -> set[int]:
    excluded: set[int] = set()
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            excluded.add(int(token))
    return excluded


@router.get(
    "/next",
    response_model=ExerciseRead,
    summary="Следующее упражнение по сложности теста",
)
async def next_exercise(
    current_user: CurrentUser,
    session: SessionDep,
    exclude: str = "",
) -> ExerciseRead:
    """Сложность берётся из последнего результата теста уровня."""
    try:
        return await service.next_exercise(
            session, current_user, parse_exclude(exclude)
        )
    except service.ExerciseNotFoundError:
        raise APIError(
            status_code=404,
            code="exercise_not_found",
            message="Упражнения для этого уровня не найдены",
        ) from None


@router.post(
    "/{exercise_id}/answer",
    response_model=AnswerFeedback,
    summary="Проверка ответа с мгновенной обратной связью",
)
async def submit_answer(
    exercise_id: int,
    data: SubmitAnswerRequest,
    current_user: CurrentUser,
) -> AnswerFeedback:
    """Возвращает результат проверки и объяснение ошибки."""
    try:
        return service.check_answer(exercise_id, data.option_id)
    except service.ExerciseNotFoundError:
        raise APIError(
            status_code=404,
            code="exercise_not_found",
            message="Упражнение не найдено",
        ) from None
    except service.InvalidOptionError:
        raise APIError(
            status_code=422,
            code="invalid_option",
            message="Выбранный вариант не относится к этому упражнению",
            field="option_id",
        ) from None
