"""Чтение и запись диалогов без управления транзакцией."""

from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.modules.dialogues.models import Dialogue, Message


class DialogueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, user_id: int, title: str, scenario: str) -> Dialogue:
        dialogue = Dialogue(user_id=user_id, title=title, scenario=scenario)
        self.session.add(dialogue)
        await self.session.flush()
        return dialogue

    async def get_owned(self, dialogue_id: int, user_id: int) -> Dialogue | None:
        return await self.session.scalar(
            select(Dialogue).where(
                Dialogue.id == dialogue_id, Dialogue.user_id == user_id
            )
        )

    async def list_owned(
        self, user_id: int, *, limit: int, offset: int
    ) -> list[Dialogue]:
        result = await self.session.scalars(
            select(Dialogue)
            .where(Dialogue.user_id == user_id)
            .order_by(Dialogue.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result)

    async def add_message(
        self, *, dialogue_id: int, role: Literal["user", "assistant"], content: str
    ) -> Message:
        message = Message(dialogue_id=dialogue_id, role=role, content=content)
        self.session.add(message)
        # Отдельный flush сохраняет порядок user → assistant даже при равном времени.
        await self.session.flush()
        return message

    async def get_messages(
        self, dialogue_id: int, *, limit: int, offset: int
    ) -> list[Message]:
        result = await self.session.scalars(
            select(Message)
            .where(Message.dialogue_id == dialogue_id)
            .order_by(Message.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result)
