import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hypothesis, HypothesisEvidence
from app.repositories.interfaces import HypothesisRepository


class PostgresHypothesisRepository(HypothesisRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, hypothesis_id: uuid.UUID) -> Hypothesis | None:
        return await self.db.get(Hypothesis, hypothesis_id)

    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Hypothesis]:
        stmt = (
            select(Hypothesis)
            .where(Hypothesis.user_id == user_id)
            .order_by(Hypothesis.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(await self.db.scalars(stmt))

    async def add(self, hypothesis: Hypothesis) -> Hypothesis:
        self.db.add(hypothesis)
        await self.db.flush()
        await self.db.refresh(hypothesis)
        return hypothesis

    async def delete(self, hypothesis: Hypothesis) -> None:
        await self.db.delete(hypothesis)
        await self.db.flush()

    async def list_evidence(self, hypothesis_id: uuid.UUID) -> list[HypothesisEvidence]:
        stmt = select(HypothesisEvidence).where(
            HypothesisEvidence.hypothesis_id == hypothesis_id
        )
        return list(await self.db.scalars(stmt))

    async def add_evidence(self, evidence: HypothesisEvidence) -> HypothesisEvidence:
        self.db.add(evidence)
        await self.db.flush()
        await self.db.refresh(evidence)
        return evidence
