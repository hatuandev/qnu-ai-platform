"""Read-only human projection, after the existing collection/binding access gate."""
import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.normalization.qnu_reader import reader_document
from app.modules.knowledge.services.qnu_serving import verify_revision_pair


async def read_source_document(db: AsyncSession, binding_id: str, revision_id: str) -> dict[str, Any]:
    revision = (await db.scalars(select(KnowledgeSourceRevision).where(
        KnowledgeSourceRevision.id == revision_id, KnowledgeSourceRevision.binding_id == binding_id))).one_or_none()
    if revision is None:
        raise AppException('Không tìm thấy bản sửa đổi nguồn.', code='SOURCE_REVISION_NOT_FOUND', status_code=404)
    document = await verify_revision_pair(revision)
    result = await asyncio.to_thread(reader_document, document)
    return {**result, 'revision_id': revision.id, 'binding_id': revision.binding_id,
            'source_pair': {k: v for k, v in ((revision.snapshot_metadata or {}).get('qnu_markdown')
                or (revision.parse_provenance or {}).get('qnu_markdown') or {}).items() if k in {'sha256', 'structured_sha256'}}}
