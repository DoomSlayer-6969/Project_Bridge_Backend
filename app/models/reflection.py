import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.hypothesis import Hypothesis
    from app.models.notification import Notification
    from app.models.user import User


class Reflection(Base):
    __tablename__ = "reflections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hypotheses.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    hypothesis: Mapped["Hypothesis"] = relationship(back_populates="reflections")
    user: Mapped["User"] = relationship(back_populates="reflections")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="reflection", cascade="all, delete-orphan", passive_deletes=True
    )
