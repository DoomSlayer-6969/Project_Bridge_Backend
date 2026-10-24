# Import every model here so `from app.models import X` works and
# Base.metadata sees all tables (needed for Alembic autogenerate).
from app.models.base import Base

__all__ = ["Base"]
