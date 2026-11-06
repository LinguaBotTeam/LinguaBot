"""Зависимости аутентификации (получение текущего пользователя)."""

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.core.errors import APIError
from linguabot.core.security import decode_access_token
from linguabot.db.session import get_session
from linguabot.modules.users.models import User
from linguabot.modules.users.repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def unauthorized(message: str = "Требуется авторизация") -> APIError:
    return APIError(status_code=401, code="unauthorized", message=message)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    session: SessionDep,
) -> User:
    if credentials is None:
        raise unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")
        user_id = int(subject)
    except (jwt.PyJWTError, TypeError, ValueError):
        raise unauthorized("Некорректный или истёкший токен")

    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise unauthorized("Пользователь не найден")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
