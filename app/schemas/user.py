import re
import uuid
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)

PHONE_PATTERN = re.compile(r"^\+?[0-9]{7,15}$")
PROFILE_PICTURE_MAX_LENGTH = 2048

Gender = Literal["male", "female", "other", "prefer_not_to_say"]


# Stripped, non-empty strings that fit their String(N) columns.
Text20 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
Text100 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Text255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    street: str
    city: str
    state: str
    country: str
    pin_code: str


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    display_name: str | None
    phone_no: str | None
    gender: str | None
    date_of_birth: date | None
    age: int | None
    profile_picture: str | None
    address: AddressResponse | None


class AddressRequest(BaseModel):
    """A complete address; it replaces the user's current one."""

    street: Text255
    city: Text100
    state: Text100
    country: Text100
    pin_code: Text20


class UserProfileUpdateRequest(BaseModel):
    """Partial update: only the fields sent are changed, and null clears a field.

    Changing `email` requires `current_password`. `address: null` removes the address.
    """

    display_name: Text100 | None = None
    phone_no: str | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None
    profile_picture: HttpUrl | None = None
    address: AddressRequest | None = None
    email: EmailStr | None = None
    current_password: str | None = None

    @field_validator("phone_no")
    @classmethod
    def valid_phone(cls, phone_no: str | None) -> str | None:
        if phone_no is not None and not PHONE_PATTERN.fullmatch(phone_no):
            raise ValueError("Phone number must be 7-15 digits with an optional leading +")
        return phone_no

    @field_validator("date_of_birth")
    @classmethod
    def not_in_future(cls, date_of_birth: date | None) -> date | None:
        if date_of_birth is not None and date_of_birth > date.today():
            raise ValueError("Date of birth can't be in the future")
        return date_of_birth

    @field_validator("profile_picture")
    @classmethod
    def fits_column(cls, url: HttpUrl | None) -> HttpUrl | None:
        if url is not None and len(str(url)) > PROFILE_PICTURE_MAX_LENGTH:
            raise ValueError(f"URL must be at most {PROFILE_PICTURE_MAX_LENGTH} characters")
        return url

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, email: str | None) -> str | None:
        return email.lower() if email is not None else None

    @model_validator(mode="after")
    def email_change_rules(self) -> Self:
        if "email" in self.model_fields_set:
            if self.email is None:
                raise ValueError("Email can't be removed")
            if self.current_password is None:
                raise ValueError("current_password is required to change the email")
        return self
