import uuid
from abc import ABC, abstractmethod

from app.models import ContextEdge


class ContextEdgeRepository(ABC):
    @abstractmethod
    async def get(self, edge_id: uuid.UUID) -> ContextEdge | None: ...

    @abstractmethod
    async def list_for_node(self, node_id: uuid.UUID) -> list[ContextEdge]:
        """Edges in either direction."""

    @abstractmethod
    async def add(self, edge: ContextEdge) -> ContextEdge:
        """Persist a new edge and return it with generated fields populated."""

    @abstractmethod
    async def delete(self, edge: ContextEdge) -> None: ...
