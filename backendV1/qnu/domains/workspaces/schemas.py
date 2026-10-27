"""DTOs for workspace administration and membership."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

WorkspaceStatus = Literal["active", "suspended"]
WorkspaceRole = Literal["admin", "editor", "reviewer", "member"]
MemberStatus = Literal["active", "pending", "revoked"]


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


class WorkspaceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)

    @field_validator("code", "name", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _strip(value)


class WorkspaceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)
    status: WorkspaceStatus | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _strip(value)


class WorkspaceResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None
    status: str
    member_count: int = 0
    created_at: datetime
    updated_at: datetime


class MemberCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor_ref: str = Field(..., min_length=2, max_length=200)
    role: WorkspaceRole = "member"
    display_name: str | None = Field(None, max_length=255)

    @field_validator("actor_ref", "display_name", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _strip(value)


class MemberUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: WorkspaceRole | None = None
    status: MemberStatus | None = None


class MemberResponse(BaseModel):
    id: str
    workspace_id: str
    actor_ref: str
    display_name: str | None = None
    role: str
    status: str
    invited_by: str | None = None
    created_at: datetime
    updated_at: datetime


class EventResponse(BaseModel):
    id: str
    workspace_id: str
    actor_ref: str | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
