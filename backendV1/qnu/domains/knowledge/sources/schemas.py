"""DTOs for knowledge sources and their immutable file revisions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RevisionResponse(BaseModel):
    id: str
    source_id: str
    revision_no: int
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
    created_by: str
    created_at: datetime


class SourceResponse(BaseModel):
    """Current view of a logical source, resolved from its latest revision."""

    id: str
    workspace_id: str
    collection_id: str
    folder_id: str | None = None
    title: str
    status: str
    revision_count: int
    current_revision_no: int
    serving_revision_no: int
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class SourceUploadResponse(BaseModel):
    source: SourceResponse
    revision: RevisionResponse


class SourceMoveRequest(BaseModel):
    target_folder_id: str | None = None


class SourceRenameRequest(BaseModel):
    title: str
