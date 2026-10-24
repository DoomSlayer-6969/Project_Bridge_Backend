import uuid
from abc import ABC, abstractmethod

from app.models import Reflection


class ReflectionRepository(ABC):
    @abstractmethod
    async def get(self, reflection_id: uuid.UUID) -> Reflection | None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Reflection]: ...

    @abstractmethod
    async def list_for_hypothesis(self, hypothesis_id: uuid.UUID) -> list[Reflection]: ...

    @abstractmethod
    async def add(self, reflection: Reflection) -> Reflection:
        """Persist a new reflection and return it with generated fields populated."""

    @abstractmethod
    async def delete(self, reflection: Reflection) -> None:
        """Delete the reflection and its notifications."""
