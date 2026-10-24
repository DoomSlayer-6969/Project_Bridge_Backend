"""FastAPI dependencies. Add one provider per repository, e.g.:

    def get_user_repo(db: SessionDep) -> UserRepository:
        return UserRepository(db)

    UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db

SessionDep = Annotated[AsyncSession, Depends(get_db)]
