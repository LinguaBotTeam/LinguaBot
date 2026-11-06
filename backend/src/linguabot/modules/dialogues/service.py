"""Создание чата, проверка владельца и ответ заглушки вместо ИИ."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.core.errors import APIError
from linguabot.modules.dialogues.models import Dialogue
from linguabot.modules.dialogues.repository import DialogueRepository
from linguabot.modules.dialogues.schemas import (
    DialogueCreate,
    DialogueRead,
    MessageCreate,
    MessagePair,
    MessageRead,
)

STUB_REPLY = "Спасибо за сообщение! Давай продолжим практику."


async def _owned_dialogue(
    repository: DialogueRepository, user_id: int, dialogue_id: int
) -> Dialogue:
    dialogue = await repository.get_owned(dialogue_id, user_id)
    if dialogue is None:
        # Одинаковый ответ не раскрывает наличие диалога другого пользователя.
        raise APIError(status_code=404, code="not_found", message="Диалог не найден")
    return dialogue


async def create_dialogue(
    session: AsyncSession, user_id: int, data: DialogueCreate
) -> DialogueRead:
    try:
        dialogue = await DialogueRepository(session).create(
            user_id=user_id, title=data.title, scenario=data.scenario
        )
        result = DialogueRead.model_validate(dialogue)
        await session.commit()
        return result
    except Exception:
        await session.rollback()
        raise


async def list_dialogues(
    session: AsyncSession, user_id: int, limit: int = 100, offset: int = 0
) -> list[DialogueRead]:
    dialogues = await DialogueRepository(session).list_owned(
        user_id, limit=limit, offset=offset
    )
    return [DialogueRead.model_validate(dialogue) for dialogue in dialogues]


async def send_message(
    session: AsyncSession, user_id: int, dialogue_id: int, data: MessageCreate
) -> MessagePair:
    repository = DialogueRepository(session)
    dialogue = await _owned_dialogue(repository, user_id, dialogue_id)
    try:
        dialogue.updated_at = datetime.now(timezone.utc)
        user_message = await repository.add_message(
            dialogue_id=dialogue.id, role="user", content=data.content
        )
        assistant_message = await repository.add_message(
            dialogue_id=dialogue.id, role="assistant", content=STUB_REPLY
        )
        result = MessagePair(
            user_message=MessageRead.model_validate(user_message),
            assistant_message=MessageRead.model_validate(assistant_message),
        )
        # CurrentUser уже начал транзакцию этой сессии. Обе записи фиксируем вместе.
        await session.commit()
        return result
    except Exception:
        await session.rollback()
        raise


async def get_history(
    session: AsyncSession,
    user_id: int,
    dialogue_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[MessageRead]:
    repository = DialogueRepository(session)
    await _owned_dialogue(repository, user_id, dialogue_id)
    messages = await repository.get_messages(dialogue_id, limit=limit, offset=offset)
    return [MessageRead.model_validate(message) for message in messages]
