import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.context_node import ContextNode
    from app.models.conversation import Conversation
    from app.models.hypothesis import Hypothesis
    from app.models.notification import Notification
    from app.models.refresh_token import RefreshToken
    from app.models.reflection import Reflection
    from app.models.user_preferences import UserPreferences


class Address(Base):
    """The User's address (a composite attribute in the ER diagram)."""

    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    street: Mapped[str | None] = mapped_column(String(255), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=False)
    pin_code: Mapped[str | None] = mapped_column(String(20), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Argon2 hash; password strength rules are enforced on the raw password in
    # app.schemas.auth.SignupRequest, since a hash can't be checked for them.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone_no: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(nullable=True)
    profile_picture: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    address_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("addresses.id", ondelete="SET NULL"), nullable=True, index=True
    )

    address: Mapped["Address | None"] = relationship()
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    preferences: Mapped["UserPreferences | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    context_nodes: Mapped[list["ContextNode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    hypotheses: Mapped[list["Hypothesis"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    reflections: Mapped[list["Reflection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def age(self) -> int | None:
        """Derived attribute: computed from date_of_birth, not stored."""
        if self.date_of_birth is None:
            return None
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
