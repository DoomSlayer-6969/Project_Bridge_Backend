import uuid
from abc import ABC, abstractmethod

from app.models import ContextNode, NodeSource


class ContextNodeRepository(ABC):
    """Context nodes and the NodeSource links to the messages they came from."""

    @abstractmethod
    async def get(self, node_id: uuid.UUID) -> ContextNode | None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> list[ContextNode]: ...

    @abstractmethod
    async def list_for_message(self, message_id: uuid.UUID) -> list[ContextNode]:
        """Nodes derived from the given message."""

    @abstractmethod
    async def add(self, node: ContextNode) -> ContextNode:
        """Persist a new node and return it with generated fields populated."""

    @abstractmethod
    async def delete(self, node: ContextNode) -> None:
        """Delete the node, its edges, sources and evidence."""

    @abstractmethod
    async def add_source(self, node_id: uuid.UUID, message_id: uuid.UUID) -> NodeSource:
        """Record that the node was derived from the message."""
