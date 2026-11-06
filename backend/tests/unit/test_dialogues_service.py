"""Storage/service guarantees using isolated, real SQLite databases."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from linguabot.core.errors import APIError
from linguabot.db.base import Base
from linguabot.modules.dialogues.models import Dialogue, Message
from linguabot.modules.dialogues.schemas import DialogueCreate, MessageCreate
from linguabot.modules.users.models import User


@asynccontextmanager
async def database(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'dialogues.db'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as session:
            owner = User(name="Owner", email="owner@example.com", password_hash="unused")
            other = User(name="Other", email="other@example.com", password_hash="unused")
            session.add_all([owner, other])
            await session.commit()
        yield engine, sessions, owner.id, other.id
    finally:
        await engine.dispose()


def test_messages_persist_in_order_across_sessions(tmp_path):
    async def scenario():
        from linguabot.modules.dialogues import service

        async with database(tmp_path) as (_, sessions, owner_id, _):
            async with sessions() as session:
                dialogue = await service.create_dialogue(session, owner_id, DialogueCreate())
                assert dialogue.title == "Новый диалог"
                assert dialogue.scenario == "free_chat"
                assert dialogue.status == "active"
                stored = await session.get(Dialogue, dialogue.id)
                assert stored.user_id == owner_id
                assert await service.get_history(session, owner_id, dialogue.id) == []
                first = await service.send_message(
                    session, owner_id, dialogue.id, MessageCreate(content="  Hello!  ")
                )
                assert first.user_message.role == "user"
                assert first.user_message.content == "Hello!"
                assert first.assistant_message.role == "assistant"
                assert first.assistant_message.content.strip()
                assert first.user_message.id < first.assistant_message.id

            async with sessions() as session:
                second = await service.send_message(
                    session, owner_id, dialogue.id, MessageCreate(content="One more turn")
                )
                assert second.assistant_message.content == first.assistant_message.content

            async with sessions() as session:
                history = await service.get_history(session, owner_id, dialogue.id)
                assert [message.id for message in history] == [
                    first.user_message.id,
                    first.assistant_message.id,
                    second.user_message.id,
                    second.assistant_message.id,
                ]
                assert [message.role for message in history] == [
                    "user", "assistant", "user", "assistant"
                ]
                assert [message.content for message in history] == [
                    "Hello!", first.assistant_message.content,
                    "One more turn", first.assistant_message.content,
                ]
                assert all(message.dialogue_id == dialogue.id for message in history)
                assert all(message.correction is None for message in history)
                page = await service.get_history(
                    session, owner_id, dialogue.id, limit=2, offset=1
                )
                assert [message.id for message in page] == [
                    first.assistant_message.id, second.user_message.id
                ]

    asyncio.run(scenario())


def test_lists_and_message_access_are_scoped_to_owner(tmp_path):
    async def scenario():
        from linguabot.modules.dialogues import service

        async with database(tmp_path) as (_, sessions, owner_id, other_id):
            async with sessions() as session:
                first = await service.create_dialogue(
                    session, owner_id, DialogueCreate(title="First")
                )
                foreign = await service.create_dialogue(
                    session, other_id, DialogueCreate(title="Foreign")
                )
                latest = await service.create_dialogue(
                    session, owner_id, DialogueCreate(title="Latest")
                )
                own = await service.list_dialogues(session, owner_id)
                assert [dialogue.id for dialogue in own] == [latest.id, first.id]
                page = await service.list_dialogues(session, owner_id, limit=1, offset=1)
                assert [dialogue.id for dialogue in page] == [first.id]
                other = await service.list_dialogues(session, other_id)
                assert [dialogue.id for dialogue in other] == [foreign.id]

            errors = []
            for dialogue_id in (foreign.id, latest.id + 1000):
                async with sessions() as session:
                    with pytest.raises(APIError) as history_error:
                        await service.get_history(session, owner_id, dialogue_id)
                    errors.append(history_error.value)
                async with sessions() as session:
                    with pytest.raises(APIError) as send_error:
                        await service.send_message(
                            session, owner_id, dialogue_id, MessageCreate(content="Forbidden")
                        )
                    errors.append(send_error.value)
            assert all(error.status_code == 404 for error in errors)
            assert all(error.code == "not_found" for error in errors)
            assert len({error.message for error in errors}) == 1
            async with sessions() as session:
                assert list(await session.scalars(select(Message))) == []

    asyncio.run(scenario())


def test_send_updates_dialogue_with_an_existing_transaction(tmp_path):
    async def scenario():
        from linguabot.modules.dialogues import service

        async with database(tmp_path) as (_, sessions, owner_id, _):
            async with sessions() as session:
                # Authentication performs a query on this same session before the service.
                await session.get(User, owner_id)
                dialogue = await service.create_dialogue(session, owner_id, DialogueCreate())
                past = datetime(2000, 1, 1)
                await session.execute(
                    update(Dialogue).where(Dialogue.id == dialogue.id).values(updated_at=past)
                )
                await session.commit()

            async with sessions() as session:
                await session.get(User, owner_id)
                assert session.in_transaction()
                await service.send_message(
                    session, owner_id, dialogue.id, MessageCreate(content="Hello")
                )
            async with sessions() as session:
                stored = await session.get(Dialogue, dialogue.id)
                assert stored.updated_at.replace(tzinfo=None) > past
                assert len(await service.get_history(session, owner_id, dialogue.id)) == 2

    asyncio.run(scenario())


def test_failed_assistant_insert_rolls_back_entire_turn(tmp_path):
    async def scenario():
        from linguabot.modules.dialogues import service

        async with database(tmp_path) as (engine, sessions, owner_id, _):
            past = datetime(2000, 1, 1)
            async with sessions() as session:
                dialogue = await service.create_dialogue(session, owner_id, DialogueCreate())
                await session.execute(
                    update(Dialogue).where(Dialogue.id == dialogue.id).values(updated_at=past)
                )
                await session.commit()
            async with engine.begin() as connection:
                await connection.execute(text("""
                    CREATE TRIGGER reject_assistant BEFORE INSERT ON messages
                    WHEN NEW.role = 'assistant'
                    BEGIN
                        SELECT RAISE(ABORT, 'assistant insert rejected');
                    END
                """))

            async with sessions() as session:
                with pytest.raises(IntegrityError, match="assistant insert rejected"):
                    await service.send_message(
                        session, owner_id, dialogue.id, MessageCreate(content="Must roll back")
                    )

            async with sessions() as session:
                assert list(await session.scalars(select(Message))) == []
                stored = await session.get(Dialogue, dialogue.id)
                assert stored.updated_at.replace(tzinfo=None) == past
                assert await service.get_history(session, owner_id, dialogue.id) == []

    asyncio.run(scenario())
