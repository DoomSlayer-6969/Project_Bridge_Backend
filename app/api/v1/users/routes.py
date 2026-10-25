from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUserDep, UserRepoDep
from app.core.jwt import verify_password
from app.models import DEFAULT_PREFERENCES, Address, User, UserPreferences
from app.schemas import (
    UserPreferencesResponse,
    UserPreferencesUpdateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["users"])

_EMAIL_TAKEN = "A user with this email already exists"


@router.get("/me", response_model=UserProfileResponse)
async def me(user: CurrentUserDep, users: UserRepoDep) -> User:
    return await users.get_with_address(user.id)


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    payload: UserProfileUpdateRequest, current_user: CurrentUserDep, users: UserRepoDep
) -> User:
    """Update the profile fields sent; null clears a field, `address: null` removes the address."""
    user = await users.get_with_address(current_user.id)
    sent = payload.model_fields_set

    if "email" in sent:
        password_ok = await run_in_threadpool(
            verify_password, payload.current_password, user.hashed_password
        )
        if not password_ok:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect password")
        if payload.email != user.email:
            if await users.get_by_email(payload.email) is not None:
                raise HTTPException(status.HTTP_409_CONFLICT, _EMAIL_TAKEN)
            user.email = payload.email

    for field in ("display_name", "phone_no", "gender", "date_of_birth"):
        if field in sent:
            setattr(user, field, getattr(payload, field))
    if "profile_picture" in sent:
        user.profile_picture = str(payload.profile_picture) if payload.profile_picture else None

    if "address" in sent:
        if payload.address is None:
            if user.address is not None:
                old_address, user.address = user.address, None
                await users.delete_address(old_address)
        elif user.address is None:
            user.address = Address(**payload.address.model_dump())
        else:
            for field, value in payload.address.model_dump().items():
                setattr(user.address, field, value)

    try:
        return await users.update(user)
    except IntegrityError:
        # A concurrent request took the email between the check and the update.
        raise HTTPException(status.HTTP_409_CONFLICT, _EMAIL_TAKEN) from None


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_preferences(user: CurrentUserDep, users: UserRepoDep) -> UserPreferences:
    """The saved preferences, or the defaults if the user hasn't saved any yet."""
    preferences = await users.get_preferences(user.id)
    return preferences or UserPreferences(user_id=user.id, **DEFAULT_PREFERENCES)


@router.patch("/me/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    payload: UserPreferencesUpdateRequest, user: CurrentUserDep, users: UserRepoDep
) -> UserPreferences:
    """Update the fields sent; the first update creates the row, with defaults for the rest."""
    preferences = await users.get_preferences(user.id)
    if preferences is None:
        preferences = UserPreferences(user_id=user.id, **DEFAULT_PREFERENCES)
    for field in payload.model_fields_set:
        setattr(preferences, field, getattr(payload, field))
    return await users.save_preferences(preferences)
