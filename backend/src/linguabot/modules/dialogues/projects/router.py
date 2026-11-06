"""API проектов: владелец определяется только авторизацией."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from linguabot.modules.auth.dependencies import CurrentUser, SessionDep
from linguabot.modules.dialogues.projects import service
from linguabot.modules.dialogues.projects.schemas import (
    ProjectCreate,
    ProjectRead,
)

router = APIRouter()
PageLimit = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0, le=2**63 - 1)]


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать свой проект диалогов",
)
async def create_project(
    data: ProjectCreate, current_user: CurrentUser, session: SessionDep
) -> ProjectRead:
    return await service.create_project(session, current_user.id, data)


@router.get(
    "", response_model=list[ProjectRead], summary="Список своих проектов"
)
async def list_projects(
    current_user: CurrentUser,
    session: SessionDep,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
) -> list[ProjectRead]:
    return await service.list_projects(session, current_user.id, limit, offset)
