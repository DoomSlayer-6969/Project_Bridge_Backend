from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.api.deps import RefreshTokenRepoDep, UserRepoDep
from app.core.jwt import (
    REFRESH_TOKEN_COOKIE,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    set_auth_cookies,
    verify_password,
    verify_token,
)
from app.models import RefreshToken, User
from app.schemas import LoginRequest, LoginResponse, SignupRequest, SignupResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# Verified against when the user doesn't exist, so a failed login takes as long
# whether or not the account exists (prevents user enumeration by timing).
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing")

# A rotated token presented again within this window is treated as two tabs
# refreshing at once rather than theft.
REFRESH_REUSE_GRACE_PERIOD = timedelta(seconds=10)


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, users: UserRepoDep) -> User:
    existing = await users.get_by_email_or_username(payload.email, payload.username)
    if existing is not None:
        field = "email" if existing.email == payload.email else "username"
        raise HTTPException(status.HTTP_409_CONFLICT, f"A user with this {field} already exists")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=await run_in_threadpool(hash_password, payload.password),
    )
    try:
        return await users.add(user)
    except IntegrityError:
        # A concurrent signup took the email/username between the check and the insert.
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A user with this email or username already exists"
        ) from None


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    users: UserRepoDep,
    refresh_tokens: RefreshTokenRepoDep,
) -> User:
    if payload.email is not None:
        user = await users.get_by_email(payload.email)
    else:
        user = await users.get_by_username(payload.username)

    hashed_password = user.hashed_password if user is not None else _DUMMY_PASSWORD_HASH
    password_ok = await run_in_threadpool(verify_password, payload.password, hashed_password)
    if user is None or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    access_token = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    await refresh_tokens.add(
        RefreshToken(
            id=refresh.jti,
            user_id=user.id,
            token_hash=hash_token(refresh.token),
            expires_at=refresh.expires_at,
        )
    )
    set_auth_cookies(response, access_token, refresh.token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_tokens: RefreshTokenRepoDep,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_TOKEN_COOKIE)] = None,
) -> None:
    """Revoke this session's refresh token and clear both cookies.

    Always succeeds: a missing, invalid, expired or already-revoked token just
    means there is nothing to revoke. The access token isn't stored, so it stays
    valid until it expires; only its cookie is removed.
    """
    clear_auth_cookies(response)
    if refresh_token is None:
        return
    try:
        claims = verify_token(refresh_token, "refresh")
    except jwt.InvalidTokenError:
        return

    row = await refresh_tokens.get(claims.jti)
    if row is None or row.token_hash != hash_token(refresh_token) or row.user_id != claims.user_id:
        return
    if row.revoked_at is None:
        await refresh_tokens.revoke(row.id)
    elif row.replaced_by_id is not None:
        # Already rotated, so presenting it again means it was copied: end every session.
        await refresh_tokens.revoke_all_for_user(row.user_id)


def _invalid_refresh_token(*, clear_cookies: bool = True) -> JSONResponse:
    # Returned rather than raised so get_db still commits (revoke_all_for_user
    # must persist) and so the cookie changes are actually sent.
    response = JSONResponse(
        {"detail": "Invalid refresh token"}, status_code=status.HTTP_401_UNAUTHORIZED
    )
    if clear_cookies:
        clear_auth_cookies(response)
    return response


@router.post(
    "/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Invalid refresh token"}},
)
async def refresh(
    refresh_tokens: RefreshTokenRepoDep,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_TOKEN_COOKIE)] = None,
) -> Response:
    """Rotate the refresh token: issue new access + refresh cookies, revoke the old token.

    Presenting an already-rotated token revokes all of the user's sessions,
    unless it was rotated within REFRESH_REUSE_GRACE_PERIOD (two tabs refreshing
    at once). In that case the cookies are left alone, since the browser may
    already hold the winning tab's new ones.
    """
    if refresh_token is None:
        return _invalid_refresh_token()
    try:
        claims = verify_token(refresh_token, "refresh")
    except jwt.InvalidTokenError:
        return _invalid_refresh_token()

    row = await refresh_tokens.get(claims.jti)
    if row is None or row.token_hash != hash_token(refresh_token) or row.user_id != claims.user_id:
        return _invalid_refresh_token()

    if row.revoked_at is not None:
        if row.replaced_by_id is None:  # logged out
            return _invalid_refresh_token()
        if datetime.now(UTC) - row.revoked_at < REFRESH_REUSE_GRACE_PERIOD:
            return _invalid_refresh_token(clear_cookies=False)
        await refresh_tokens.revoke_all_for_user(row.user_id)
        return _invalid_refresh_token()

    new_refresh = create_refresh_token(row.user_id)
    await refresh_tokens.add(
        RefreshToken(
            id=new_refresh.jti,
            user_id=row.user_id,
            token_hash=hash_token(new_refresh.token),
            expires_at=new_refresh.expires_at,
        )
    )
    if not await refresh_tokens.revoke(row.id, replaced_by_id=new_refresh.jti):
        # A concurrent request rotated this token first. Raising rolls back the
        # row added above; the cookies are left for the winning request's.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    set_auth_cookies(response, create_access_token(row.user_id), new_refresh.token)
    return response
