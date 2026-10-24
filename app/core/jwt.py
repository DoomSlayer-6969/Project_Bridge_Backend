"""Password hashing, JWT access/refresh tokens, and the auth cookies that carry them.

Token errors surface as `jwt.InvalidTokenError` (PyJWT's base class, which
also covers expired tokens); callers catch that one type.
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from fastapi import Response
from pwdlib import PasswordHash

from app.core.config import settings

TokenType = Literal["access", "refresh"]

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"

_password_hash = PasswordHash.recommended()  # Argon2


# --- Passwords ---------------------------------------------------------------
# Argon2 is deliberately slow; call these via run_in_threadpool from async code.


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _password_hash.verify(password, hashed_password)


# --- Tokens ------------------------------------------------------------------


@dataclass(frozen=True)
class IssuedRefreshToken:
    """A new refresh token plus what the caller must persist as a RefreshToken row."""

    token: str
    jti: uuid.UUID
    expires_at: datetime


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    token_type: TokenType
    jti: uuid.UUID
    expires_at: datetime


def _encode(user_id: uuid.UUID, token_type: TokenType, jti: uuid.UUID, expires_at: datetime) -> str:
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "jti": str(jti),
        "iat": datetime.now(UTC),
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return _encode(user_id, "access", uuid.uuid4(), expires_at)


def create_refresh_token(user_id: uuid.UUID) -> IssuedRefreshToken:
    jti = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return IssuedRefreshToken(_encode(user_id, "refresh", jti, expires_at), jti, expires_at)


def verify_token(token: str, expected_type: TokenType) -> TokenClaims:
    """Check signature, expiry and type. Raises jwt.InvalidTokenError on any failure.

    For refresh tokens this only proves the token is genuine; the caller must
    still check the RefreshToken row (exists, hash matches, not revoked).
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "type", "jti", "iat", "exp"]},
    )
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError(f"Expected a {expected_type} token")
    try:
        user_id, jti = uuid.UUID(payload["sub"]), uuid.UUID(payload["jti"])
    except ValueError as exc:
        raise jwt.InvalidTokenError("Malformed token claims") from exc
    return TokenClaims(user_id, payload["type"], jti, datetime.fromtimestamp(payload["exp"], UTC))


def hash_token(token: str) -> str:
    """SHA-256 of a token, for storing refresh tokens without keeping them usable."""
    return hashlib.sha256(token.encode()).hexdigest()


# --- Cookies -----------------------------------------------------------------


def _refresh_cookie_path() -> str:
    # Only send the refresh token to the auth routes, not to every request.
    return f"{settings.api_v1_prefix}/auth"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=_refresh_cookie_path(),
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        ACCESS_TOKEN_COOKIE, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax"
    )
    response.delete_cookie(
        REFRESH_TOKEN_COOKIE,
        path=_refresh_cookie_path(),
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
