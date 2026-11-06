"""Маршруты теста уровня."""

from fastapi import APIRouter, status

from linguabot.core.errors import APIError
from linguabot.modules.assessment import service
from linguabot.modules.assessment.schemas import (
    QuestionsResponse,
    SubmitTestRequest,
    TestResultRead,
)
from linguabot.modules.auth.dependencies import CurrentUser, SessionDep

router = APIRouter()


@router.get(
    "/questions",
    response_model=QuestionsResponse,
    summary="Вопросы теста уровня",
)
async def questions(current_user: CurrentUser) -> QuestionsResponse:
    """Возвращает пять фиксированных вопросов без правильных ответов."""
    return service.get_questions()


@router.post(
    "/submit",
    response_model=TestResultRead,
    status_code=status.HTTP_201_CREATED,
    summary="Отправка ответов и сохранение результата",
)
async def submit(
    data: SubmitTestRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> TestResultRead:
    """Проверяет ответы, сохраняет результат и возвращает уровень."""
    try:
        result = await service.submit_test(session, current_user, data)
    except service.InvalidAnswersError:
        raise APIError(
            status_code=422,
            code="invalid_answers",
            message="Ответы должны покрывать все вопросы теста одним вариантом каждый",
        ) from None
    return TestResultRead.from_model(result)


@router.get(
    "/result",
    response_model=TestResultRead,
    summary="Последний сохранённый результат",
)
async def result(current_user: CurrentUser, session: SessionDep) -> TestResultRead:
    saved = await service.get_latest_result(session, current_user)
    if saved is None:
        raise APIError(
            status_code=404,
            code="result_not_found",
            message="Тест ещё не пройден",
        )
    return TestResultRead.from_model(saved)
