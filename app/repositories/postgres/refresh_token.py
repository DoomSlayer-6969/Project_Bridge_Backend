import uuid

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken
from app.repositories.interfaces import RefreshTokenRepository


class PostgresRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, token_id: uuid.UUID) -> RefreshToken | None:
        return await self.db.get(RefreshToken, token_id)

    async def add(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token

    async def revoke(self, token_id: uuid.UUID, replaced_by_id: uuid.UUID | None = None) -> bool:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=func.now(), replaced_by_id=replaced_by_id)
            .execution_options(synchronize_session="fetch")
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=func.now())
            .execution_options(synchronize_session="fetch")
        )
        await self.db.execute(stmt)
