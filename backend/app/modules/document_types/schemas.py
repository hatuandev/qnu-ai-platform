"""Pydantic DTOs for document type management and synchronization."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DocumentTypeCategory = Literal["legal_internal", "administrative", "academic", "forms"]


class DocumentTypeCreateRequest(BaseModel):
    """Payload for adding a custom document type."""

    code: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    name: str = Field(..., min_length=2, max_length=255)
    category: DocumentTypeCategory
    description: str | None = Field(None, max_length=4000)
    priority: int = Field(5, ge=1, le=10)
    retention_period: str | None = Field(None, max_length=64)

    @field_validator("code", "name", "description", "retention_period", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class DocumentTypeUpdateRequest(BaseModel):
    """Payload for changing display metadata without changing the code."""

    name: str | None = Field(None, min_length=2, max_length=255)
    category: DocumentTypeCategory | None = None
    description: str | None = Field(None, max_length=4000)
    priority: int | None = Field(None, ge=1, le=10)
    retention_period: str | None = Field(None, max_length=64)
    is_active: bool | None = None

    @field_validator("name", "description", "retention_period", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class DocumentTypeResponse(BaseModel):
    """Document type item exposed to the Platform UI and API consumers."""

    id: str
    code: str
    name: str
    category: DocumentTypeCategory
    category_name: str
    description: str | None = None
    priority: int
    retention_period: str | None = None
    nd30: bool
    is_active: bool
    is_system_default: bool
    is_custom: bool
    doc_count: int = 0
    source_system: str
    source_version: str | None = None
    source_hash: str | None = None
    synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DocumentTypeSyncResponse(BaseModel):
    """Result of importing the canonical taxonomy into Platform storage."""

    taxonomy_version: str
    source_system: str
    source_hash: str
    added: int
    updated: int
    deactivated: int
    skipped: int
    total: int
    synced_at: datetime
