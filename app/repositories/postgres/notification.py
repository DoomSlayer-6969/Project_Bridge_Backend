import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification
from app.repositories.interfaces import NotificationRepository


class PostgresNotificationRepository(NotificationRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, notification_id: uuid.UUID) -> Notification | None:
        return await self.db.get(Notification, notification_id)

    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.scheduled_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(await self.db.scalars(stmt))

    async def add(self, notification: Notification) -> Notification:
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    async def delete(self, notification: Notification) -> None:
        await self.db.delete(notification)
        await self.db.flush()
