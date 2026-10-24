import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContextNode, NodeSource
from app.repositories.interfaces import ContextNodeRepository


class PostgresContextNodeRepository(ContextNodeRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, node_id: uuid.UUID) -> ContextNode | None:
        return await self.db.get(ContextNode, node_id)

    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> list[ContextNode]:
        stmt = (
            select(ContextNode)
            .where(ContextNode.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )
        return list(await self.db.scalars(stmt))

    async def list_for_message(self, message_id: uuid.UUID) -> list[ContextNode]:
        stmt = (
            select(ContextNode)
            .join(NodeSource, NodeSource.node_id == ContextNode.id)
            .where(NodeSource.message_id == message_id)
        )
        return list(await self.db.scalars(stmt))

    async def add(self, node: ContextNode) -> ContextNode:
        self.db.add(node)
        await self.db.flush()
        await self.db.refresh(node)
        return node

    async def delete(self, node: ContextNode) -> None:
        await self.db.delete(node)
        await self.db.flush()

    async def add_source(self, node_id: uuid.UUID, message_id: uuid.UUID) -> NodeSource:
        source = NodeSource(node_id=node_id, message_id=message_id)
        self.db.add(source)
        await self.db.flush()
        return source
