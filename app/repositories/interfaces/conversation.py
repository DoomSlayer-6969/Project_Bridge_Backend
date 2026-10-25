import uuid
from abc import ABC, abstractmethod

from app.models import Conversation


class ConversationRepository(ABC):
    @abstractmethod
    async def get(self, conversation_id: uuid.UUID) -> Conversation | None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Conversation]:
        """Newest first."""

    @abstractmethod
    async def add(self, conversation: Conversation) -> Conversation:
        """Persist a new conversation and return it with generated fields populated."""

    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation:
        """Persist changes made to a loaded conversation."""

    @abstractmethod
    async def delete(self, conversation: Conversation) -> None:
        """Delete the conversation and its messages."""
