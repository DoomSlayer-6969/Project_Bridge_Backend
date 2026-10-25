from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

# Allowed modes aren't decided yet: any stripped, non-empty string that fits String(32).
DefaultMode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class UserPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    default_mode: str
    memory_allowed: bool
    reflection_allowed: bool
    notification_enabled: bool


class UserPreferencesUpdateRequest(BaseModel):
    """Partial update: only the fields sent are changed. Null isn't allowed (the columns are NOT NULL)."""

    default_mode: DefaultMode | None = None
    memory_allowed: bool | None = None
    reflection_allowed: bool | None = None
    notification_enabled: bool | None = None

    @field_validator("*")
    @classmethod
    def not_null(cls, value: Any) -> Any:
        # Runs only for fields that were sent, so omitting a field is still fine.
        if value is None:
            raise ValueError("Can't be null")
        return value
