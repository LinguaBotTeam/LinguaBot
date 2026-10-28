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
from linguabot.integrations.llm import ModelReply


class DeterministicModel:
    async def generate(self, messages):
        return ModelReply(reply="Hello! Let us practice.", correction=None)


@pytest.fixture(autouse=True)
def offline_model(monkeypatch):
    from linguabot.modules.dialogues import service

    monkeypatch.setattr(service, "get_language_model", lambda: DeterministicModel(), raising=False)


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
            async with engine.begin() as connection:
                await connection.execute(text("DROP TRIGGER reject_assistant"))
            async with sessions() as session:
                retry = await service.send_message(
                    session, owner_id, dialogue.id, MessageCreate(content="Retry after storage failure")
                )
                assert retry.assistant_message.content == "Hello! Let us practice."

    asyncio.run(scenario())


def test_model_receives_topic_latest_level_current_text_and_only_owned_history(tmp_path):
    async def scenario():
        from linguabot.modules.dialogues import service
        from linguabot.modules.dialogues.repository import DialogueRepository
        from linguabot.modules.assessment.models import TestResult

        captured = []

        class CorrectingModel:
            async def generate(self, messages):
                captured.append(messages)
                return ModelReply(reply="What would you like to drink?", correction="Нужно: I am hungry.")

        async with database(tmp_path) as (_, sessions, owner_id, other_id):
            async with sessions() as session:
                dialogue = await service.create_dialogue(session, owner_id, DialogueCreate(scenario="cafe"))
                foreign = await service.create_dialogue(session, other_id, DialogueCreate())
                another = await service.create_dialogue(session, owner_id, DialogueCreate())
                repository = DialogueRepository(session)
                await repository.add_message(dialogue_id=foreign.id, role="user", content="FOREIGN HISTORY")
                await repository.add_message(dialogue_id=another.id, role="user", content="OTHER DIALOGUE")
                await repository.add_message(dialogue_id=dialogue.id, role="user", content="Hello!")
                await repository.add_message(dialogue_id=dialogue.id, role="assistant", content="Welcome!")
                session.add_all([
                    TestResult(user_id=owner_id, score=1, level="beginner", cefr="A1", details={}, taken_at=datetime(2000, 1, 1)),
                    TestResult(user_id=owner_id, score=2, level="intermediate", cefr=" b2 ", details={}, taken_at=datetime(2001, 1, 1)),
                    TestResult(user_id=other_id, score=3, level="advanced", cefr="C2", details={}, taken_at=datetime(2002, 1, 1)),
                ])
                await session.commit()
                pair = await service.send_message(session, owner_id, dialogue.id,
                    MessageCreate(content="I is hungry."), language_model=CorrectingModel())
                assert pair.user_message.correction == "Нужно: I am hungry."
                assert pair.assistant_message.content == "What would you like to drink?"
                assert pair.assistant_message.correction is None
            async with sessions() as session:
                history = await service.get_history(session, owner_id, dialogue.id)
                assert history[-2].correction == "Нужно: I am hungry."
                assert history[-1].correction is None
                assert len(list(await session.scalars(select(TestResult)))) == 3
        messages = captured[0]
        assert "cafe" in messages[0].content
        assert "B2" in messages[0].content
        assert [(m.role, m.content) for m in messages[1:]] == [
            ("user", "Hello!"), ("assistant", "Welcome!"), ("user", "I is hungry."),
        ]
        assert all("owner@example.com" not in m.content and "Owner" not in m.content for m in messages)

    asyncio.run(scenario())


@pytest.mark.parametrize("level,cefr,want", [(None, None, "A1"), ("intermediate", None, "B1"), ("unknown", "bad", "A1")])
def test_assessment_fallback_reaches_model(tmp_path, level, cefr, want):
    async def scenario():
        from linguabot.modules.dialogues import service
        from linguabot.modules.assessment.models import TestResult

        class LevelModel:
            async def generate(self, messages):
                assert f"CEFR level {want}." in messages[0].content
                return ModelReply(reply="Hello!", correction=None)

        async with database(tmp_path) as (_, sessions, owner_id, _):
            async with sessions() as session:
                dialogue = await service.create_dialogue(session, owner_id, DialogueCreate())
                if level is not None:
                    session.add(TestResult(user_id=owner_id, score=1, level=level, cefr=cefr, details={}))
                    await session.commit()
                pair = await service.send_message(session, owner_id, dialogue.id, MessageCreate(content="Hello!"), language_model=LevelModel())
                assert pair.user_message.correction is None

    asyncio.run(scenario())


@pytest.mark.parametrize("contents,expected", [
    ([f"turn {i}" for i in range(15)], [f"turn {i}" for i in range(3, 15)]),
    (["old", "я" * 1500, "🙂" * 400, "recent"], ["🙂" * 400, "recent"]),
    (["old", "x" * 4000], ["x" * 4000]),
    (["old", "я" * 4000], []),
])
def test_model_history_is_recent_chronological_and_complete_with_byte_budget(tmp_path, contents, expected):
    async def scenario():
        from linguabot.modules.dialogues import service
        from linguabot.modules.dialogues.repository import DialogueRepository

        class HistoryModel:
            async def generate(self, messages):
                assert [m.content for m in messages[1:-1]] == expected
                assert messages[-1].content == "я" * 4000
                return ModelReply(reply="Hello!", correction=None)

        async with database(tmp_path) as (_, sessions, owner_id, _):
            async with sessions() as session:
                dialogue = await service.create_dialogue(session, owner_id, DialogueCreate())
                for content in contents:
                    await DialogueRepository(session).add_message(dialogue_id=dialogue.id, role="user", content=content)
                await session.commit()
                await service.send_message(session, owner_id, dialogue.id,
                    MessageCreate(content="я" * 4000), language_model=HistoryModel())
                history = await service.get_history(session, owner_id, dialogue.id)
                assert [m.content for m in history[:-2]] == contents

    asyncio.run(scenario())


@pytest.mark.parametrize("kind,status", [("unavailable", 503), ("invalid", 502), ("malformed", 502), ("settings", 503)])
def test_model_failure_rolls_back_messages_and_timestamp_and_releases_admission(tmp_path, monkeypatch, kind, status):
    async def scenario():
        from linguabot.modules.dialogues import service
        from linguabot.integrations.llm import LLMUnavailableError, LLMInvalidResponseError, LLMSettings

        class FailingModel:
            async def generate(self, messages):
                if kind == "unavailable":
                    raise LLMUnavailableError()
                if kind == "invalid":
                    raise LLMInvalidResponseError()
                return {"reply": "", "correction": None, "private": "provider detail"}

        if kind == "settings":
            monkeypatch.setattr(service, "get_language_model", lambda: LLMSettings(_env_file=None, base_url="https://example.com/private"))
        async with database(tmp_path) as (_, sessions, owner_id, _):
            past = datetime(2000, 1, 1)
            async with sessions() as session:
                dialogue = await service.create_dialogue(session, owner_id, DialogueCreate())
                await session.execute(update(Dialogue).where(Dialogue.id == dialogue.id).values(updated_at=past))
                await session.commit()
            async with sessions() as session:
                kwargs = {} if kind == "settings" else {"language_model": FailingModel()}
                with pytest.raises(APIError) as error:
                    await service.send_message(session, owner_id, dialogue.id, MessageCreate(content="Hello!"), **kwargs)
                assert error.value.status_code == status
                assert "private" not in str(error.value) and "provider detail" not in str(error.value)
                assert not session.in_transaction()
            async with sessions() as session:
                assert list(await session.scalars(select(Message))) == []
                assert (await session.get(Dialogue, dialogue.id)).updated_at.replace(tzinfo=None) == past
                await service.send_message(session, owner_id, dialogue.id, MessageCreate(content="Retry"), language_model=DeterministicModel())

    asyncio.run(scenario())


def test_ownership_is_checked_before_factory_history_and_assessment(tmp_path, monkeypatch):
    async def scenario():
        from linguabot.modules.dialogues import service
        from linguabot.modules.dialogues.repository import DialogueRepository
        from linguabot.modules.assessment.repository import TestResultRepository

        def forbidden(*args, **kwargs):
            pytest.fail("Foreign dialogue reached protected context or model")

        monkeypatch.setattr(service, "get_language_model", forbidden)
        monkeypatch.setattr(DialogueRepository, "get_recent_messages", forbidden, raising=False)
        monkeypatch.setattr(TestResultRepository, "get_latest_by_user", forbidden)
        async with database(tmp_path) as (_, sessions, owner_id, other_id):
            async with sessions() as session:
                dialogue = await service.create_dialogue(session, other_id, DialogueCreate())
                for dialogue_id in (dialogue.id, dialogue.id + 1000):
                    with pytest.raises(APIError) as error:
                        await service.send_message(session, owner_id, dialogue_id, MessageCreate(content="Hello"))
                    assert error.value.status_code == 404

    asyncio.run(scenario())


def test_overlapping_turn_is_rejected_then_retry_uses_committed_history(tmp_path):
    async def scenario():
        from linguabot.modules.dialogues import service

        started, release = asyncio.Event(), asyncio.Event()
        histories = []

        class PausedModel:
            async def generate(self, messages):
                histories.append([m.content for m in messages[1:]])
                started.set()
                await release.wait()
                return ModelReply(reply="First reply", correction=None)

        class RetryModel:
            async def generate(self, messages):
                histories.append([m.content for m in messages[1:]])
                return ModelReply(reply="Next reply", correction=None)

        async with database(tmp_path) as (_, sessions, owner_id, _):
            async with sessions() as session:
                dialogue = await service.create_dialogue(session, owner_id, DialogueCreate())
                another = await service.create_dialogue(session, owner_id, DialogueCreate())
            async with sessions() as first_session, sessions() as second_session:
                first = asyncio.create_task(service.send_message(first_session, owner_id, dialogue.id,
                    MessageCreate(content="First turn"), language_model=PausedModel()))
                try:
                    await asyncio.wait_for(started.wait(), timeout=2)
                    with pytest.raises(APIError) as error:
                        await asyncio.wait_for(service.send_message(second_session, owner_id, dialogue.id,
                            MessageCreate(content="Overlapping turn"), language_model=RetryModel()), timeout=2)
                    assert error.value.status_code == 409
                    # A separate dialogue remains usable while the model is awaiting a response.
                    await service.send_message(second_session, owner_id, another.id,
                        MessageCreate(content="Independent"), language_model=DeterministicModel())
                finally:
                    release.set()
                    await first
            async with sessions() as session:
                await service.send_message(session, owner_id, dialogue.id,
                    MessageCreate(content="Retry turn"), language_model=RetryModel())
                assert len(await service.get_history(session, owner_id, dialogue.id)) == 4
            assert histories == [["First turn"], ["First turn", "First reply", "Retry turn"]]

    asyncio.run(scenario())


def test_cancelled_generation_releases_admission_without_partial_turn(tmp_path):
    async def scenario():
        from linguabot.modules.dialogues import service

        started = asyncio.Event()

        class PausedModel:
            async def generate(self, messages):
                started.set()
                await asyncio.Event().wait()

        async with database(tmp_path) as (_, sessions, owner_id, _):
            async with sessions() as session:
                dialogue = await service.create_dialogue(session, owner_id, DialogueCreate())
            async with sessions() as session:
                task = asyncio.create_task(service.send_message(session, owner_id, dialogue.id,
                    MessageCreate(content="Cancelled"), language_model=PausedModel()))
                try:
                    await asyncio.wait_for(started.wait(), timeout=2)
                finally:
                    task.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await task
                assert not session.in_transaction()
            async with sessions() as session:
                assert await service.get_history(session, owner_id, dialogue.id) == []
                retry = await service.send_message(session, owner_id, dialogue.id,
                    MessageCreate(content="Retry"), language_model=DeterministicModel())
                assert retry.user_message.content == "Retry"

    asyncio.run(scenario())
