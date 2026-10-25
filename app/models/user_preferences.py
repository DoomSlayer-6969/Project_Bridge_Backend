import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User

# Used until the user saves their own preferences: every pipeline is opt-in.
DEFAULT_PREFERENCES = {
    "default_mode": "general",
    "memory_allowed": False,
    "reflection_allowed": False,
    "notification_enabled": False,
}


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    # 1:1 with User, so the FK is also the primary key.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    default_mode: Mapped[str] = mapped_column(String(32))
    memory_allowed: Mapped[bool]
    reflection_allowed: Mapped[bool]
    notification_enabled: Mapped[bool]

    user: Mapped["User"] = relationship(back_populates="preferences")
