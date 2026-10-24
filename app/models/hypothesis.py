import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.hypothesis_evidence import HypothesisEvidence
    from app.models.reflection import Reflection
    from app.models.user import User


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    statement_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="hypotheses")
    evidence: Mapped[list["HypothesisEvidence"]] = relationship(
        back_populates="hypothesis", cascade="all, delete-orphan", passive_deletes=True
    )
    reflections: Mapped[list["Reflection"]] = relationship(
        back_populates="hypothesis", cascade="all, delete-orphan", passive_deletes=True
    )
