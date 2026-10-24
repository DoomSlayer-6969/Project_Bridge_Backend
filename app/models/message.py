import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.hypothesis_evidence import HypothesisEvidence
    from app.models.node_source import NodeSource


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    sender: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    active_mode: Mapped[str] = mapped_column(String(32))
    memory_allowed: Mapped[bool]

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    node_sources: Mapped[list["NodeSource"]] = relationship(
        back_populates="message", cascade="all, delete-orphan", passive_deletes=True
    )
    evidence: Mapped[list["HypothesisEvidence"]] = relationship(
        back_populates="message", cascade="all, delete-orphan", passive_deletes=True
    )
