"""Личные диалоги с ограниченным контекстом и атомарной записью ответа ИИ."""

from datetime import datetime, timezone
from threading import Lock

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.ai.prompts.dialogue import build_messages, normalize_level
from linguabot.core.errors import APIError
from linguabot.integrations.llm import (
    ChatMessage, LanguageModel, LLMInvalidResponseError, LLMUnavailableError,
    ModelReply, get_language_model,
)
from linguabot.modules.assessment.repository import TestResultRepository
from linguabot.modules.dialogues.models import Dialogue
from linguabot.modules.dialogues.repository import DialogueRepository
from linguabot.modules.dialogues.schemas import (
    DialogueCreate,
    DialogueRead,
    MessageCreate,
    MessagePair,
    MessageRead,
)

# Single-process admission only: no asyncio lock retained across event loops.
# The mutex protects just the set operations, never database or network work.
_admission_mutex = Lock()
_active_dialogues: set[int] = set()


def _admit(dialogue_id: int) -> None:
    if not _admission_mutex.acquire(blocking=False):
        raise APIError(409, "conflict", "Повторите отправку сообщения чуть позже")
    try:
        if dialogue_id in _active_dialogues:
            raise APIError(409, "conflict", "Ответ в этом диалоге ещё готовится")
        _active_dialogues.add(dialogue_id)
    finally:
        _admission_mutex.release()


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
    session: AsyncSession, user_id: int, dialogue_id: int, data: MessageCreate,
    *, language_model: LanguageModel | None = None,
) -> MessagePair:
    repository = DialogueRepository(session)
    dialogue = await _owned_dialogue(repository, user_id, dialogue_id)
    _admit(dialogue_id)
    try:
        if language_model is None:
            try:
                language_model = get_language_model()
            except ValidationError:
                raise LLMUnavailableError() from None
        assessment = await TestResultRepository(session).get_latest_by_user(user_id)
        level = normalize_level(assessment.cefr, assessment.level) if assessment else "A1"
        history = await repository.get_recent_messages(dialogue_id)
        messages = build_messages(
            scenario=dialogue.scenario, level=level,
            history=[ChatMessage(role=message.role, content=message.content) for message in history],
            content=data.content,
        )
        generated = await language_model.generate(messages)
        # Validate the replaceable boundary too, before touching persistent state.
        reply = ModelReply.model_validate(
            generated.model_dump() if isinstance(generated, ModelReply) else generated
        )
        dialogue.updated_at = datetime.now(timezone.utc)
        user_message = await repository.add_message(
            dialogue_id=dialogue.id, role="user", content=data.content, correction=reply.correction
        )
        assistant_message = await repository.add_message(
            dialogue_id=dialogue.id, role="assistant", content=reply.reply
        )
        result = MessagePair(
            user_message=MessageRead.model_validate(user_message),
            assistant_message=MessageRead.model_validate(assistant_message),
        )
        # CurrentUser уже начал транзакцию этой сессии. Обе записи фиксируем вместе.
        await session.commit()
        return result
    except LLMUnavailableError:
        await session.rollback()
        raise APIError(503, "service_unavailable", "Локальная модель временно недоступна") from None
    except (LLMInvalidResponseError, ValidationError):
        await session.rollback()
        raise APIError(502, "bad_gateway", "Модель вернула некорректный ответ") from None
    except BaseException:
        await session.rollback()
        raise
    finally:
        with _admission_mutex:
            _active_dialogues.discard(dialogue_id)


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
