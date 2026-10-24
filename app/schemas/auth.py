import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
