"""Модель результата теста уровня."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from linguabot.db.base import Base


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[int] = mapped_column()
    level: Mapped[str] = mapped_column(String(24))
    cefr: Mapped[str | None] = mapped_column(String(4))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
