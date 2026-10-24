import uuid
from abc import ABC, abstractmethod

from app.models import RefreshToken


class RefreshTokenRepository(ABC):
    """Issued refresh tokens, stored by hash and rotated on use."""

    @abstractmethod
    async def get(self, token_id: uuid.UUID) -> RefreshToken | None:
        """Look up by the token's `jti` claim."""

    @abstractmethod
    async def add(self, token: RefreshToken) -> RefreshToken:
        """Persist a newly issued token and return it with generated fields populated."""

    @abstractmethod
    async def revoke(self, token_id: uuid.UUID, replaced_by_id: uuid.UUID | None = None) -> None:
        """Revoke one token if still active; on rotation, record its replacement."""

    @abstractmethod
    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke every active token of the user (logout everywhere / reuse detected)."""
