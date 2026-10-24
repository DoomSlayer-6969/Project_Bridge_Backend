import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message
from app.repositories.interfaces import MessageRepository


class PostgresMessageRepository(MessageRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, message_id: uuid.UUID) -> Message | None:
        return await self.db.get(Message, message_id)

    async def list_for_conversation(
        self, conversation_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(offset)
            .limit(limit)
        )
        return list(await self.db.scalars(stmt))

    async def add(self, message: Message) -> Message:
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def delete(self, message: Message) -> None:
        await self.db.delete(message)
        await self.db.flush()
