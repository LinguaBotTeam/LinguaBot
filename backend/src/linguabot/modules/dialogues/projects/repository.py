"""Хранение проектов с обязательным ограничением по владельцу."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.modules.dialogues.projects.models import DialogueProject


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, user_id: int, name: str) -> DialogueProject:
        project = DialogueProject(user_id=user_id, name=name)
        self.session.add(project)
        await self.session.flush()
        return project

    async def get_owned(
        self, project_id: int, user_id: int
    ) -> DialogueProject | None:
        return await self.session.scalar(
            select(DialogueProject).where(
                DialogueProject.id == project_id,
                DialogueProject.user_id == user_id,
            )
        )

    async def list_owned(
        self, user_id: int, *, limit: int, offset: int
    ) -> list[DialogueProject]:
        result = await self.session.scalars(
            select(DialogueProject)
            .where(DialogueProject.user_id == user_id)
            .order_by(DialogueProject.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result)
