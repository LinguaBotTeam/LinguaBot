"""API личных текстовых диалогов. Все операции требуют входа."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from linguabot.modules.auth.dependencies import CurrentUser, SessionDep
from linguabot.modules.dialogues import service
from linguabot.modules.dialogues.schemas import (
    DialogueCreate,
    DialogueRead,
    MessageCreate,
    MessagePair,
    MessageRead,
)

router = APIRouter()

# SQLAlchemy Integer соответствует int4 в PostgreSQL и поддерживается SQLite.
DialogueId = Annotated[int, Path(ge=1, le=2**31 - 1)]
PageLimit = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0, le=2**63 - 1)]


@router.post(
    "",
    response_model=DialogueRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать свой диалог",
)
async def create_dialogue(
    data: DialogueCreate, current_user: CurrentUser, session: SessionDep
) -> DialogueRead:
    return await service.create_dialogue(session, current_user.id, data)


@router.get("", response_model=list[DialogueRead], summary="Список своих диалогов")
async def list_dialogues(
    current_user: CurrentUser,
    session: SessionDep,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
) -> list[DialogueRead]:
    return await service.list_dialogues(session, current_user.id, limit, offset)


@router.post(
    "/{dialogue_id}/messages",
    response_model=MessagePair,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить сообщение и получить ответ локального ИИ",
    description=(
        "Практика английского по сценарию диалога; пояснение ошибки на русском "
        "сохраняется в correction сообщения пользователя. При сбое модели пара "
        "не записывается. Одновременная отправка в тот же диалог возвращает 409."
    ),
)
async def send_message(
    dialogue_id: DialogueId,
    data: MessageCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> MessagePair:
    return await service.send_message(session, current_user.id, dialogue_id, data)


@router.get(
    "/{dialogue_id}/messages",
    response_model=list[MessageRead],
    summary="История своего диалога",
)
async def get_history(
    dialogue_id: DialogueId,
    current_user: CurrentUser,
    session: SessionDep,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
) -> list[MessageRead]:
    return await service.get_history(session, current_user.id, dialogue_id, limit, offset)
