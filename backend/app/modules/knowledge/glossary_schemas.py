"""Pydantic DTOs for collection glossary management.

Create/update payloads deliberately exclude status, reviewer and timestamp
fields: the server owns the approval lifecycle and clients can never submit
an already-approved entry.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints
from typing_extensions import TypedDict

GlossaryStatus = Literal["pending", "approved", "rejected", "revoked"]
GlossaryReviewAction = Literal["approve", "reject", "revoke"]

ScopeLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ScopeYear = Annotated[StrictInt, Field(ge=1000, le=9999)]


class GlossaryScope(TypedDict, total=False):
    __pydantic_config__ = ConfigDict(extra="forbid")

    years: Annotated[list[ScopeYear], Field(max_length=10)]
    methods: Annotated[list[ScopeLabel], Field(max_length=20)]
    entities: Annotated[list[ScopeLabel], Field(max_length=20)]


class GlossaryTermCreate(BaseModel):
    user_phrase: str = Field(min_length=1, max_length=200)
    target_term: str = Field(min_length=1, max_length=200)
    note: str = Field(default="", max_length=1000)
    scope: GlossaryScope = Field(default_factory=dict)


class GlossaryTermUpdate(BaseModel):
    user_phrase: str | None = Field(default=None, min_length=1, max_length=200)
    target_term: str | None = Field(default=None, min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=1000)
    scope: GlossaryScope | None = None
    expected_version: int = Field(ge=1)


class GlossaryReview(BaseModel):
    action: GlossaryReviewAction
    reason: str | None = Field(default=None, max_length=512)
    expected_version: int = Field(ge=1)


class GlossarySettingsUpdate(BaseModel):
    is_enabled: bool
    expected_version: int = Field(ge=1)


class GlossaryTermResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    user_phrase: str
    target_term: str
    note: str = ""
    scope: dict[str, Any] = Field(default_factory=dict)
    status: str
    created_by: str | None = None
    updated_by: str | None = None
    reviewed_by: str | None = None
    review_reason: str | None = None
    reviewed_at: datetime | None = None
    version: int
    updated_at: datetime | None = None


class GlossaryTermListResponse(BaseModel):
    items: list[GlossaryTermResponse]
    total: int
    page: int
    page_size: int


class GlossarySettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    collection_id: str
    is_enabled: bool
    version: int
    updated_by: str | None = None
    updated_at: datetime | None = None
