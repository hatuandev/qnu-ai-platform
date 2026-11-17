"""System spelling settings HTTP API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_db
from qnu.domains.identity.permissions import require_permission
from qnu.domains.ocr.review.defaults import SpellingDefaults, read, save

router = APIRouter(
    prefix="/settings/spelling",
    tags=["Settings"],
    dependencies=[Depends(require_permission("ai.models.manage"))],
)


@router.get("", response_model=SpellingDefaults)
async def get_defaults(db: AsyncSession = Depends(get_db)) -> SpellingDefaults:
    return await read(db)


@router.put("", response_model=SpellingDefaults)
async def update_defaults(
    body: SpellingDefaults, db: AsyncSession = Depends(get_db)
) -> SpellingDefaults:
    return await save(db, body)
