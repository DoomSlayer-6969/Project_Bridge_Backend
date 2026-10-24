import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.context_node import ContextNode
    from app.models.hypothesis import Hypothesis
    from app.models.message import Message


class HypothesisEvidence(Base):
    """Links a hypothesis to the message and/or context node supporting it."""

    __tablename__ = "hypothesis_evidence"
    __table_args__ = (
        CheckConstraint(
            "message_id IS NOT NULL OR node_id IS NOT NULL", name="has_source"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hypotheses.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("context_nodes.id", ondelete="CASCADE"), index=True
    )
    evidence_role: Mapped[str] = mapped_column(String(32))

    hypothesis: Mapped["Hypothesis"] = relationship(back_populates="evidence")
    message: Mapped["Message | None"] = relationship(back_populates="evidence")
    node: Mapped["ContextNode | None"] = relationship(back_populates="evidence")
