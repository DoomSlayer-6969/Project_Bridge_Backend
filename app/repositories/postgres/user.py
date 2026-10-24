import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserPreferences
from app.repositories.interfaces import UserRepository


class PostgresUserRepository(UserRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self.db.scalar(select(User).where(User.email == email))

    async def get_by_email_or_username(self, email: str, username: str) -> User | None:
        stmt = select(User).where(or_(User.email == email, User.username == username)).limit(1)
        return await self.db.scalar(stmt)

    async def add(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()

    async def get_preferences(self, user_id: uuid.UUID) -> UserPreferences | None:
        return await self.db.get(UserPreferences, user_id)

    async def save_preferences(self, preferences: UserPreferences) -> UserPreferences:
        preferences = await self.db.merge(preferences)
        await self.db.flush()
        return preferences
