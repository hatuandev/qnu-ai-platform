"""Preview and commit endpoints for the review handoff."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_db
from qnu.contracts.pagination import Page
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.review import service
from qnu.domains.knowledge.review.models import ReviewSubmissionPreview
from qnu.domains.knowledge.review.schemas import (
    SubmissionCommitRequest,
    SubmissionDetail,
    SubmissionOutcome,
    SubmissionPreviewRequest,
    SubmissionPreviewResponse,
    SubmissionResponse,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}/review-submissions",
    tags=["Knowledge · Review handoff"],
)
Key = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"),
]
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]
StatusFilter = Literal["pending", "changes_requested", "resolved", "cancelled"]


@router.post("/previews", response_model=SubmissionPreviewResponse)
async def create_preview(
    workspace_id: str,
    collection_id: str,
    body: SubmissionPreviewRequest,
    db: DB,
    actor: Actor,
) -> ReviewSubmissionPreview:
    return await service.create_preview(db, actor, workspace_id, collection_id, body)


@router.post("", response_model=SubmissionOutcome)
async def commit_submission(
    workspace_id: str,
    collection_id: str,
    body: SubmissionCommitRequest,
    idempotency_key: Key,
    db: DB,
    actor: Actor,
) -> SubmissionOutcome:
    return await service.commit_submission(
        db, actor, workspace_id, collection_id, body, idempotency_key
    )


@router.get("", response_model=Page[SubmissionResponse])
async def list_submissions(
    workspace_id: str,
    collection_id: str,
    db: DB,
    actor: Actor,
    status: StatusFilter | None = Query(None),
    document_id: str | None = Query(None, min_length=1, max_length=64),
    version_id: str | None = Query(None, min_length=1, max_length=64),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[SubmissionResponse]:
    return await service.list_submissions(
        db,
        actor,
        workspace_id,
        collection_id,
        status=status,
        document_id=document_id,
        version_id=version_id,
        page=page,
        page_size=page_size,
    )


@router.get("/{submission_id}", response_model=SubmissionDetail)
async def submission_detail(
    workspace_id: str,
    collection_id: str,
    submission_id: str,
    db: DB,
    actor: Actor,
) -> SubmissionDetail:
    return await service.submission_detail(db, actor, workspace_id, collection_id, submission_id)
