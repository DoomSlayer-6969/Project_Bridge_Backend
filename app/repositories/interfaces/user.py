import uuid
from abc import ABC, abstractmethod

from app.models import User, UserPreferences


class UserRepository(ABC):
    """Users and their 1:1 preferences."""

    @abstractmethod
    async def get(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_email_or_username(self, email: str, username: str) -> User | None:
        """A user whose email or username matches, if any."""

    @abstractmethod
    async def add(self, user: User) -> User:
        """Persist a new user and return it with generated fields populated."""

    @abstractmethod
    async def delete(self, user: User) -> None:
        """Delete the user and everything owned by it."""

    @abstractmethod
    async def get_preferences(self, user_id: uuid.UUID) -> UserPreferences | None: ...

    @abstractmethod
    async def save_preferences(self, preferences: UserPreferences) -> UserPreferences:
        """Create the user's preferences, or overwrite the existing ones."""
