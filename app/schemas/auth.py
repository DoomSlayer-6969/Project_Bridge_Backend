import uuid

from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

PASSWORD_MIN_LENGTH = 8


class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1)
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, email: str) -> str:
        return email.lower()

    @field_validator("password")
    @classmethod
    def strong_password(cls, password: str) -> str:
        missing = [
            requirement
            for requirement, ok in [
                (f"at least {PASSWORD_MIN_LENGTH} characters", len(password) >= PASSWORD_MIN_LENGTH),
                ("an uppercase letter", any(c.isupper() for c in password)),
                ("a lowercase letter", any(c.islower() for c in password)),
                ("a number", any(c.isdigit() for c in password)),
                ("a special character", any(not c.isalnum() for c in password)),
            ]
            if not ok
        ]
        if missing:
            raise ValueError("Password must contain " + ", ".join(missing))
        return password


class SignupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str


class LoginRequest(BaseModel):
    """Password plus exactly one of email or username."""

    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=1)
    # No strength rules here: they apply when a password is set, not when it's checked.
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, email: str | None) -> str | None:
        return email.lower() if email is not None else None

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> Self:
        if (self.email is None) == (self.username is None):
            raise ValueError("Provide exactly one of email or username")
        return self


class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
