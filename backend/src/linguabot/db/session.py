"""Асинхронный движок и фабрика сессий."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from linguabot.core.config import settings
from linguabot.db.base import Base

engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_models() -> None:
    """Создаёт таблицы, если их ещё нет."""
    from linguabot.modules.users import models  # noqa: F401  (регистрация моделей)
    from linguabot.modules.dialogues import models as dialogue_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
