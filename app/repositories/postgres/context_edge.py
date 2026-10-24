import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContextEdge
from app.repositories.interfaces import ContextEdgeRepository


class PostgresContextEdgeRepository(ContextEdgeRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, edge_id: uuid.UUID) -> ContextEdge | None:
        return await self.db.get(ContextEdge, edge_id)

    async def list_for_node(self, node_id: uuid.UUID) -> list[ContextEdge]:
        stmt = select(ContextEdge).where(
            or_(ContextEdge.from_node_id == node_id, ContextEdge.to_node_id == node_id)
        )
        return list(await self.db.scalars(stmt))

    async def add(self, edge: ContextEdge) -> ContextEdge:
        self.db.add(edge)
        await self.db.flush()
        await self.db.refresh(edge)
        return edge

    async def delete(self, edge: ContextEdge) -> None:
        await self.db.delete(edge)
        await self.db.flush()
