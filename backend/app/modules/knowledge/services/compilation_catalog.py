"""Server-owned source sets and exact proof catalog, independent of publication."""
import asyncio
import hashlib
from types import SimpleNamespace

from sqlalchemy import select

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.services.compilation_contracts import evidence_catalog
from app.modules.knowledge.services.scope_helper import get_scoped_collection
from app.modules.knowledge.services.wiki_compiler import digest, source_units


def invalid(reason: str, status: int = 409) -> AppException:
    return AppException('Bản biên soạn chưa đủ điều kiện hoặc nguồn đã thay đổi.',
        code='KNOWLEDGE_COMPILATION_INVALID', status_code=status, details={'reason': reason})


def require(actor, permission: str) -> None:
    if not actor or not actor.authenticated or not actor.actor_id or not actor.has_permission(permission):
        raise AppException('Bạn không có quyền thực hiện thao tác này.', code='forbidden', status_code=403)


async def load_sources(db, collection_id: str, ids: list[str], actor, *, lock: bool = False) -> tuple:
    require(actor, 'ai.knowledge.view')
    if not ids or len(ids) > 16 or len(ids) != len(set(ids)):
        raise invalid('source_ids', 422)
    collection = await get_scoped_collection(db, collection_id, actor=actor, for_update=lock)
    if not collection.is_active:
        raise invalid('collection_inactive')
    query = (select(KnowledgeSourceRevision, KnowledgeBinding)
        .join(KnowledgeBinding, KnowledgeBinding.id == KnowledgeSourceRevision.binding_id)
        .where(KnowledgeBinding.collection_id == collection_id, KnowledgeSourceRevision.id.in_(ids))
        .order_by(KnowledgeBinding.id))
    if lock:
        query = query.with_for_update()
    rows = (await db.execute(query.execution_options(populate_existing=True))).all()
    if len(rows) != len(ids) or len({binding.id for _, binding in rows}) != len(ids):
        raise invalid('source_not_in_collection')
    sources, identities = [], []
    for source, binding in rows:
        latest = await db.scalar(select(KnowledgeSourceRevision.id).where(
            KnowledgeSourceRevision.binding_id == binding.id).order_by(KnowledgeSourceRevision.revision_no.desc()).limit(1))
        if (latest != source.id or source.status != 'ready' or binding.status not in {'pending', 'active'}
                or (source.quality_report or {}).get('overall_status') == 'failed'):
            raise invalid('source_not_current_ready')
        raw = await storage_service.get(source.snapshot_storage_path)
        if raw is None or hashlib.sha256(raw).hexdigest() != source.origin_file_hash:
            raise invalid('raw_source_hash')
        frozen = SimpleNamespace(**{column.key: getattr(source, column.key) for column in source.__table__.columns},
                                 collection_id=collection_id)
        await asyncio.to_thread(source_units, frozen)
        sources.append(frozen)
        identities.append({'source_revision_id': source.id, 'binding_id': binding.id,
            'canonical_hash': source.canonical_hash, 'origin_file_hash': source.origin_file_hash,
            'lock_version': source.lock_version, 'binding_status': binding.status,
            'artifact_hash': digest(source.parse_provenance), 'quality_hash': digest(source.quality_report),
            'active_index_revision_id': binding.active_index_revision_id,
            'active_source_revision_id': binding.active_source_revision_id})
    catalog = await asyncio.to_thread(evidence_catalog, sources, collection_id)
    fingerprint = digest({'sources': identities, 'catalog': catalog, 'collection_epoch': collection.index_epoch})
    return collection, sources, catalog, fingerprint


def dependency_catalog(sources: list, catalog: dict) -> dict:
    """Only explicit native context/parent references; metadata is not semantic proof."""
    by_source_unit = {(ref['source_revision_id'], ref['unit_id']): pid for pid, ref in catalog.items()}
    dependencies = {}
    for source in sources:
        units = source_units(source)
        for unit in units:
            pid = by_source_unit.get((source.id, unit.id))
            if pid is None:
                continue
            linked = [*unit.context_refs, *(uid for refs in unit.field_context_refs.values() for uid in refs)]
            if unit.parent_id:
                linked.append(unit.parent_id)
            dependencies[pid] = sorted({by_source_unit[(source.id, uid)] for uid in linked
                if (source.id, uid) in by_source_unit and uid != unit.id})
    return dependencies


def temporal_catalog(sources: list, catalog: dict) -> dict:
    """Reuse the existing TemporalScope and milestone precision, without promoting its status."""
    temporal = {(s.id, u.id): u.temporal.model_dump(exclude_none=True, exclude_defaults=True)
                for s in sources for u in source_units(s)}
    return {pid: temporal[(ref['source_revision_id'], ref['unit_id'])] for pid, ref in catalog.items()}
