"""Advanced topic compilation API; publication remains a separate existing workflow."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.compilation_runtime_schemas import CompilationAction, CompilationRequest
from app.modules.knowledge.services import compilation_service as service

router = APIRouter()


@router.get('/collections/{collection_id}/compilations/preview')
async def preview_compilation(collection_id: str, source_revision_ids: list[str] = Query(..., min_length=1, max_length=16),
        db: AsyncSession = Depends(get_db), actor: AuthActor = Depends(require_permission('ai.knowledge.upload'))) -> dict:
    return await service.preview(db, collection_id, source_revision_ids, actor)


@router.post('/collections/{collection_id}/compilations')
async def create_compilation(collection_id: str, request: CompilationRequest,
        db: AsyncSession = Depends(get_db), actor: AuthActor = Depends(require_permission('ai.knowledge.upload'))) -> dict:
    return await service.create(db, collection_id, request, actor)


@router.get('/collections/{collection_id}/compilations')
async def list_compilations(collection_id: str, db: AsyncSession = Depends(get_db),
        actor: AuthActor = Depends(require_permission('ai.knowledge.review'))) -> dict:
    return await service.list_compilations(db, collection_id, actor)


@router.get('/collections/{collection_id}/compilations/{job_id}')
async def get_compilation(collection_id: str, job_id: str, db: AsyncSession = Depends(get_db),
        actor: AuthActor = Depends(require_permission('ai.knowledge.review'))) -> dict:
    return await service.read(db, collection_id, job_id, actor)


@router.post('/collections/{collection_id}/compilations/{job_id}/decisions')
async def decide_compilation(collection_id: str, job_id: str, request: CompilationAction,
        db: AsyncSession = Depends(get_db), actor: AuthActor = Depends(require_permission('ai.knowledge.review'))) -> dict:
    return await service.decide(db, collection_id, job_id, request, actor)
