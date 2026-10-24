import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation
from app.repositories.interfaces import ConversationRepository


class PostgresConversationRepository(ConversationRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self.db.get(Conversation, conversation_id)

    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(await self.db.scalars(stmt))

    async def add(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def delete(self, conversation: Conversation) -> None:
        await self.db.delete(conversation)
        await self.db.flush()
