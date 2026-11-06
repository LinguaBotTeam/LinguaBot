"""Доступ к данным результатов теста."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from linguabot.modules.assessment.models import TestResult


class TestResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        score: int,
        level: str,
        cefr: str | None,
        details: dict,
    ) -> TestResult:
        result = TestResult(
            user_id=user_id,
            score=score,
            level=level,
            cefr=cefr,
            details=details,
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def get_latest_by_user(self, user_id: int) -> TestResult | None:
        result = await self.session.execute(
            select(TestResult)
            .where(TestResult.user_id == user_id)
            .order_by(TestResult.taken_at.desc(), TestResult.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
