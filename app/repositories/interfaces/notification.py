import uuid
from abc import ABC, abstractmethod

from app.models import Notification


class NotificationRepository(ABC):
    @abstractmethod
    async def get(self, notification_id: uuid.UUID) -> Notification | None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Notification]:
        """Latest scheduled first."""

    @abstractmethod
    async def add(self, notification: Notification) -> Notification:
        """Persist a new notification and return it with generated fields populated."""

    @abstractmethod
    async def delete(self, notification: Notification) -> None: ...
