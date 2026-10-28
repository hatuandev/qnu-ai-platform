"""DTOs for knowledge directory hierarchy (folders)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: str | None = None


class FolderUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class FolderMoveRequest(BaseModel):
    target_parent_id: str | None = None


class FolderResponse(BaseModel):
    id: str
    workspace_id: str
    collection_id: str
    parent_id: str | None = None
    name: str
    source_count: int = 0
    subfolder_count: int = 0
    created_by: str
    created_at: datetime
    updated_at: datetime


class FolderBreadcrumbItem(BaseModel):
    id: str
    name: str


class FolderDetailResponse(FolderResponse):
    breadcrumbs: list[FolderBreadcrumbItem] = Field(default_factory=list)


class FolderImpactResponse(BaseModel):
    folder_id: str
    folder_name: str
    subfolder_count: int
    source_count: int
    descendant_folder_ids: list[str]

