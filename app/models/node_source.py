import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.context_node import ContextNode
    from app.models.message import Message


class NodeSource(Base):
    """M:N link: which messages a context node was derived from."""

    __tablename__ = "node_sources"

    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("context_nodes.id", ondelete="CASCADE"), primary_key=True
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    node: Mapped["ContextNode"] = relationship(back_populates="sources")
    message: Mapped["Message"] = relationship(back_populates="node_sources")
