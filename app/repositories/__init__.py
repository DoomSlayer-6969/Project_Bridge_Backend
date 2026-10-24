# interfaces/: abstract repository contracts (what each repository can do).
# postgres/:   PostgreSQL implementations of those contracts (how it's done).
# Each repository depends only on its interface, AsyncSession and app.models;
# repositories never import or call each other.
from app.repositories.interfaces import (
    ContextEdgeRepository,
    ContextNodeRepository,
    ConversationRepository,
    HypothesisRepository,
    MessageRepository,
    NotificationRepository,
    RefreshTokenRepository,
    ReflectionRepository,
    UserRepository,
)
from app.repositories.postgres import (
    PostgresContextEdgeRepository,
    PostgresContextNodeRepository,
    PostgresConversationRepository,
    PostgresHypothesisRepository,
    PostgresMessageRepository,
    PostgresNotificationRepository,
    PostgresRefreshTokenRepository,
    PostgresReflectionRepository,
    PostgresUserRepository,
)

__all__ = [
    "ContextEdgeRepository",
    "ContextNodeRepository",
    "ConversationRepository",
    "HypothesisRepository",
    "MessageRepository",
    "NotificationRepository",
    "RefreshTokenRepository",
    "ReflectionRepository",
    "UserRepository",
    "PostgresContextEdgeRepository",
    "PostgresContextNodeRepository",
    "PostgresConversationRepository",
    "PostgresHypothesisRepository",
    "PostgresMessageRepository",
    "PostgresNotificationRepository",
    "PostgresRefreshTokenRepository",
    "PostgresReflectionRepository",
    "PostgresUserRepository",
]
