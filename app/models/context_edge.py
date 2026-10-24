import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.context_node import ContextNode


class ContextEdge(Base):
    __tablename__ = "context_edges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("context_nodes.id", ondelete="CASCADE"), index=True
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("context_nodes.id", ondelete="CASCADE"), index=True
    )
    relation_type: Mapped[str] = mapped_column(String(64))

    from_node: Mapped["ContextNode"] = relationship(
        foreign_keys=[from_node_id], back_populates="outgoing_edges"
    )
    to_node: Mapped["ContextNode"] = relationship(
        foreign_keys=[to_node_id], back_populates="incoming_edges"
    )
