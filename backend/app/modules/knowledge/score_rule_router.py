"""Authenticated management endpoints; controller delegates all rule operations."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.score_rule_schemas import (
    RuleAction,
    RuleDraft,
    RuleImport,
    RulePreview,
    RuleRegistry,
)
from app.modules.knowledge.services import score_rule_service
from app.modules.rag.score_conversion_schemas import ScoreConversionResult

router = APIRouter(prefix="/collections/{collection_id}/score-rules", tags=["Score rules"])


@router.get("", response_model=RuleRegistry)
async def list_rules(collection_id: str, db: AsyncSession = Depends(get_db),
                     actor: AuthActor = Depends(require_permission("ai.knowledge.view"))) -> RuleRegistry:
    return await score_rule_service.list_rules(db, actor, collection_id)


@router.post("", response_model=RuleRegistry, status_code=201)
async def create_rule(collection_id: str, body: RuleDraft, db: AsyncSession = Depends(get_db),
                      actor: AuthActor = Depends(require_permission("ai.knowledge.update"))) -> RuleRegistry:
    return await score_rule_service.create_draft(db, actor, collection_id, body)


@router.post("/{rule_id}/preview", response_model=ScoreConversionResult)
async def preview_rule(collection_id: str, rule_id: str, body: RulePreview,
                       db: AsyncSession = Depends(get_db),
                       actor: AuthActor = Depends(require_permission("ai.knowledge.view"))) -> ScoreConversionResult:
    return await score_rule_service.preview(db, actor, collection_id, rule_id, body)


@router.post("/{rule_id}/actions", response_model=RuleRegistry)
async def act_on_rule(collection_id: str, rule_id: str, body: RuleAction,
                      db: AsyncSession = Depends(get_db),
                      actor: AuthActor = Depends(require_permission("ai.knowledge.review"))) -> RuleRegistry:
    return await score_rule_service.transition(db, actor, collection_id, rule_id, body)


@router.post("/import", response_model=RuleRegistry, status_code=201)
async def import_rules(collection_id: str, body: RuleImport, db: AsyncSession = Depends(get_db),
                       actor: AuthActor = Depends(require_permission("ai.knowledge.update"))) -> RuleRegistry:
    return await score_rule_service.import_drafts(db, actor, collection_id, body)
