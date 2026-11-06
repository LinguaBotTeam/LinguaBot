"""Assignment transactions use real storage and synthetic data only."""

import asyncio
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from linguabot.db.base import Base
from linguabot.modules.dialogues.models import Dialogue, Message
from linguabot.modules.dialogues.projects.models import DialogueProject
from linguabot.modules.users.models import User


@pytest.mark.parametrize("fail_commit", [False, True])
def test_assignment_preserves_messages_and_rolls_back_on_failure(
    tmp_path, monkeypatch, fail_commit
):
    async def scenario():
        from linguabot.modules.dialogues import service
        from linguabot.modules.dialogues.schemas import DialogueProjectChange

        engine = create_async_engine(
            f"sqlite+aiosqlite:///{tmp_path / 'projects.db'}"
        )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with sessions() as session:
                user = User(name="Synthetic", email="synthetic@example.com",
                            password_hash="unused-synthetic-hash")
                session.add(user)
                await session.flush()
                project = DialogueProject(user_id=user.id, name="Trip")
                dialogue = Dialogue(user_id=user.id, title="Airport",
                                    scenario="cafe", status="active")
                session.add_all([project, dialogue])
                await session.flush()
                message = Message(
                    dialogue_id=dialogue.id, role="user", content="I is here",
                    correction="I am here", created_at=datetime(2000, 1, 1),
                )
                session.add(message)
                await session.commit()
                ids = user.id, dialogue.id, project.id, message.id
                expected_message = (
                    message.dialogue_id, message.role, message.content,
                    message.correction, message.created_at,
                )
                expected_dialogue = (
                    dialogue.user_id, dialogue.title, dialogue.scenario,
                    dialogue.status, dialogue.created_at,
                )
            user_id, dialogue_id, project_id, message_id = ids
            async with sessions() as session:
                if fail_commit:
                    async def reject_commit():
                        await session.flush()
                        raise RuntimeError("Synthetic commit failure")

                    monkeypatch.setattr(session, "commit", reject_commit)
                    with pytest.raises(RuntimeError, match="Synthetic"):
                        await service.change_project(
                            session, user_id, dialogue_id,
                            DialogueProjectChange(project_id=project_id),
                        )
                    assert not session.in_transaction()
                else:
                    await service.change_project(
                        session, user_id, dialogue_id,
                        DialogueProjectChange(project_id=project_id),
                    )
            async with sessions() as session:
                stored = await session.get(Dialogue, dialogue_id)
                assert stored.project_id == (
                    None if fail_commit else project_id)
                assert (stored.user_id, stored.title, stored.scenario,
                        stored.status, stored.created_at) == expected_dialogue
                message = await session.get(Message, message_id)
                assert (message.dialogue_id, message.role, message.content,
                        message.correction,
                        message.created_at) == expected_message
        finally:
            await engine.dispose()

    asyncio.run(scenario())
