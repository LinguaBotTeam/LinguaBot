"""Доступ к данным пользователей."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.modules.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == self._normalize_email(email))
        )
        return result.scalar_one_or_none()

    async def create(self, *, name: str, email: str, password_hash: str) -> User:
        user = User(
            name=name.strip(),
            email=self._normalize_email(email),
            password_hash=password_hash,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
