"""Создание и чтение проектов текущего пользователя."""

from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.modules.dialogues.projects.repository import ProjectRepository
from linguabot.modules.dialogues.projects.schemas import (
    ProjectCreate,
    ProjectRead,
)


async def create_project(
    session: AsyncSession, user_id: int, data: ProjectCreate
) -> ProjectRead:
    try:
        project = await ProjectRepository(session).create(
            user_id=user_id, name=data.name
        )
        result = ProjectRead.model_validate(project)
        await session.commit()
        return result
    except Exception:
        await session.rollback()
        raise


async def list_projects(
    session: AsyncSession, user_id: int, limit: int = 100, offset: int = 0
) -> list[ProjectRead]:
    projects = await ProjectRepository(session).list_owned(
        user_id, limit=limit, offset=offset
    )
    return [ProjectRead.model_validate(project) for project in projects]
