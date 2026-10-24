import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.context_edge import ContextEdge
    from app.models.hypothesis_evidence import HypothesisEvidence
    from app.models.node_source import NodeSource
    from app.models.user import User


class ContextNode(Base):
    __tablename__ = "context_nodes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    node_type: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(255))
    review_status: Mapped[str] = mapped_column(String(32))

    user: Mapped["User"] = relationship(back_populates="context_nodes")
    outgoing_edges: Mapped[list["ContextEdge"]] = relationship(
        foreign_keys="ContextEdge.from_node_id",
        back_populates="from_node",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    incoming_edges: Mapped[list["ContextEdge"]] = relationship(
        foreign_keys="ContextEdge.to_node_id",
        back_populates="to_node",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sources: Mapped[list["NodeSource"]] = relationship(
        back_populates="node", cascade="all, delete-orphan", passive_deletes=True
    )
    evidence: Mapped[list["HypothesisEvidence"]] = relationship(
        back_populates="node", cascade="all, delete-orphan", passive_deletes=True
    )
