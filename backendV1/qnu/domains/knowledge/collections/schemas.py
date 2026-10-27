"""DTOs for knowledge collections."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


class CollectionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _strip(value)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tên kho tri thức không được để trống.")
        return value


class CollectionUpdateRequest(BaseModel):
    """Partial update; omitted fields keep their value, ``null`` clears description."""

    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _strip(value)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Tên kho tri thức không được để trống.")
        return value


class CollectionResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    source_count: int = 0
    created_by: str
    created_at: datetime
    updated_at: datetime
