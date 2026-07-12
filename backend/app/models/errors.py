from typing import Any

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Safe human-readable error message.")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional safe structured error metadata.",
    )


class ApiErrorResponse(BaseModel):
    error: ApiError = Field(description="Application error details.")
