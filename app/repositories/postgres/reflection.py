import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Reflection
from app.repositories.interfaces import ReflectionRepository


class PostgresReflectionRepository(ReflectionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, reflection_id: uuid.UUID) -> Reflection | None:
        return await self.db.get(Reflection, reflection_id)

    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Reflection]:
        stmt = (
            select(Reflection)
            .where(Reflection.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )
        return list(await self.db.scalars(stmt))

    async def list_for_hypothesis(self, hypothesis_id: uuid.UUID) -> list[Reflection]:
        stmt = select(Reflection).where(Reflection.hypothesis_id == hypothesis_id)
        return list(await self.db.scalars(stmt))

    async def add(self, reflection: Reflection) -> Reflection:
        self.db.add(reflection)
        await self.db.flush()
        await self.db.refresh(reflection)
        return reflection

    async def delete(self, reflection: Reflection) -> None:
        await self.db.delete(reflection)
        await self.db.flush()
