import uuid
from abc import ABC, abstractmethod

from app.models import Message


class MessageRepository(ABC):
    @abstractmethod
    async def get(self, message_id: uuid.UUID) -> Message | None: ...

    @abstractmethod
    async def list_for_conversation(
        self, conversation_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> list[Message]:
        """Oldest first, i.e. chat order."""

    @abstractmethod
    async def add(self, message: Message) -> Message:
        """Persist a new message and return it with generated fields populated."""

    @abstractmethod
    async def delete(self, message: Message) -> None: ...
