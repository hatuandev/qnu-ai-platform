"""DTOs for knowledge sources and their immutable file revisions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from qnu.domains.knowledge.index.schemas import IndexReadiness
from qnu.domains.knowledge.policies.capabilities import SummaryCapabilities
from qnu.domains.ocr.schemas import ProcessingRunResponse


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
    processing: ProcessingRunResponse | None = None


class SourceUploadResponse(BaseModel):
    source: SourceResponse
    revision: RevisionResponse


class SourceMoveRequest(BaseModel):
    target_folder_id: str | None = None


class SourceRenameRequest(BaseModel):
    title: str


class SourceTextVersionRef(BaseModel):
    id: str
    version: int
    canonical_sha256: str
    markdown_sha256: str
    created_by: str
    created_at: datetime


class SourceProcessingRunSummary(ProcessingRunResponse):
    """Latest saved text of this run; it is not a claim about the serving version."""

    latest_text_version: SourceTextVersionRef | None = None


class SourceVersionRef(BaseModel):
    version_id: str
    version_no: int
    state_version: int
    status: str
    bundle_sha256: str
    document_id: str
    document_title: str


class SourceDerivation(BaseModel):
    """One exact Compiler input rooted in this source revision, never newest-wins."""

    compilation_run_id: str
    compilation_generation: int
    compilation_status: str
    origin: str
    ocr_run_id: str
    ocr_generation: int
    text_version: SourceTextVersionRef | None = None
    version: SourceVersionRef | None = None
    readiness: IndexReadiness | None = None
    is_serving: bool = False


class SourceServingState(BaseModel):
    """Three distinct revisions: being prepared, published, actually served."""

    served_revision_no: int | None = None
    preparing_revision_no: int | None = None
    published_revision_no: int | None = None
    served_version_id: str | None = None
    served_document_id: str | None = None


class SourceActionPermissions(BaseModel):
    can_stop: bool
    can_withdraw: bool
    can_update: bool
    can_delete: bool


class SourcePreparationSummary(BaseModel):
    intent_id: str
    status: str
    step: str
    error_code: str | None = None


class SourceSummaryResponse(BaseModel):
    observed_at: datetime
    source_id: str
    title: str
    latest_revision_no: int
    serving_revision_no: int
    revision: RevisionResponse
    processing_runs: list[SourceProcessingRunSummary]
    runs_truncated: bool
    active_run_id: str | None
    derivations: list[SourceDerivation]
    derivations_truncated: bool
    capabilities: SummaryCapabilities
    serving: SourceServingState
    actions: SourceActionPermissions
    preparation: SourcePreparationSummary | None = None
