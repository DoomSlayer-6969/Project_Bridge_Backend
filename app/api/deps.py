"""FastAPI dependencies: the DB session, one provider per repository, and auth.

Route operations annotate parameters with the `<X>RepoDep` aliases, which are
typed as the repository *interface*; the providers below choose the concrete
PostgreSQL implementation. Switching databases means changing only this file.
Protect a route by taking a `CurrentUserDep` parameter.
"""

from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from app.core.jwt import ACCESS_TOKEN_COOKIE, verify_token
from app.models import User
from app.repositories import (
    ContextEdgeRepository,
    ContextNodeRepository,
    ConversationRepository,
    HypothesisRepository,
    MessageRepository,
    NotificationRepository,
    PostgresContextEdgeRepository,
    PostgresContextNodeRepository,
    PostgresConversationRepository,
    PostgresHypothesisRepository,
    PostgresMessageRepository,
    PostgresNotificationRepository,
    PostgresRefreshTokenRepository,
    PostgresReflectionRepository,
    PostgresUserRepository,
    RefreshTokenRepository,
    ReflectionRepository,
    UserRepository,
)

SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_user_repo(db: SessionDep) -> UserRepository:
    return PostgresUserRepository(db)


def get_conversation_repo(db: SessionDep) -> ConversationRepository:
    return PostgresConversationRepository(db)


def get_message_repo(db: SessionDep) -> MessageRepository:
    return PostgresMessageRepository(db)


def get_context_node_repo(db: SessionDep) -> ContextNodeRepository:
    return PostgresContextNodeRepository(db)


def get_context_edge_repo(db: SessionDep) -> ContextEdgeRepository:
    return PostgresContextEdgeRepository(db)


def get_hypothesis_repo(db: SessionDep) -> HypothesisRepository:
    return PostgresHypothesisRepository(db)


def get_reflection_repo(db: SessionDep) -> ReflectionRepository:
    return PostgresReflectionRepository(db)


def get_notification_repo(db: SessionDep) -> NotificationRepository:
    return PostgresNotificationRepository(db)


def get_refresh_token_repo(db: SessionDep) -> RefreshTokenRepository:
    return PostgresRefreshTokenRepository(db)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
ConversationRepoDep = Annotated[ConversationRepository, Depends(get_conversation_repo)]
MessageRepoDep = Annotated[MessageRepository, Depends(get_message_repo)]
ContextNodeRepoDep = Annotated[ContextNodeRepository, Depends(get_context_node_repo)]
ContextEdgeRepoDep = Annotated[ContextEdgeRepository, Depends(get_context_edge_repo)]
HypothesisRepoDep = Annotated[HypothesisRepository, Depends(get_hypothesis_repo)]
ReflectionRepoDep = Annotated[ReflectionRepository, Depends(get_reflection_repo)]
NotificationRepoDep = Annotated[NotificationRepository, Depends(get_notification_repo)]
RefreshTokenRepoDep = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repo)]


async def get_current_user(
    users: UserRepoDep,
    access_token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
) -> User:
    """The user identified by the access-token cookie; 401 if absent, invalid or expired."""
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if access_token is None:
        raise unauthorized
    try:
        claims = verify_token(access_token, "access")
    except jwt.InvalidTokenError:
        raise unauthorized from None
    user = await users.get(claims.user_id)
    if user is None:  # deleted after the token was issued
        raise unauthorized
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
