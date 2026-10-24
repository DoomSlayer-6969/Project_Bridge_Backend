from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.api.deps import UserRepoDep
from app.core.jwt import hash_password
from app.models import User
from app.schemas import SignupRequest, SignupResponse

router = APIRouter(prefix="/auth", tags=["auth"])


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
