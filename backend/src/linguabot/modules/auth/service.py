"""Бизнес-логика регистрации и входа."""

from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.core.security import create_access_token, hash_password, verify_password
from linguabot.core.config import settings
from linguabot.modules.auth.schemas import LoginRequest, LoginResponse, RegisterRequest
from linguabot.modules.users.models import User
from linguabot.modules.users.repository import UserRepository


class EmailAlreadyRegisteredError(Exception):
    """Email уже занят другим аккаунтом."""


class InvalidCredentialsError(Exception):
    """Неверная пара email/пароль."""


async def register_user(session: AsyncSession, data: RegisterRequest) -> User:
    repository = UserRepository(session)
    if await repository.get_by_email(data.email) is not None:
        raise EmailAlreadyRegisteredError
    return await repository.create(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
    )


async def authenticate_user(session: AsyncSession, data: LoginRequest) -> User:
    repository = UserRepository(session)
    user = await repository.get_by_email(data.email)
    if user is None or not verify_password(data.password, user.password_hash):
        raise InvalidCredentialsError
    return user


def build_login_response(user: User) -> LoginResponse:
    return LoginResponse(
        access_token=create_access_token(str(user.id)),
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user,
    )
