"""Context corrections must retain cell evidence and create reviewable derivatives."""

import pytest

from app.modules.knowledge.services.source_artifact import build_source_artifact


def test_context_edit_preserves_original_evidence_and_requires_review():
    from app.modules.knowledge.schemas import SourceContextEditRequest
    from app.modules.knowledge.services.source_context import apply_context_edits

    artifact = build_source_artifact("| Ngành | Điểm chuẩn 2023 |\n| --- | --- |\n| Một ngành học | 15 |", 1, {})
    old = artifact["facts"][0]
    request = SourceContextEditRequest(expected_fact_set_hash=artifact["fact_set_hash"], reason="Đối chiếu trang gốc",
                                      facts=[{"fact_id": old["id"], "year": 2024, "method": "THPT"}])
    revised = apply_context_edits(artifact, request, "actor_fixture")
    assert artifact["facts"][0]["raw_data"]["temporal_context"]["year"] == 2023
    assert revised["facts"][0]["raw_data"]["temporal_context"]["year"] == 2024
    assert revised["facts"][0]["raw_data"]["header_path"] == old["raw_data"]["header_path"]
    assert revised["facts"][0]["attribute_value"] == "15"
    assert revised["review"]["status"] == "required"
    assert revised["context_audit"]["actor_id"] == "actor_fixture"
    assert revised["fact_set_hash"] != artifact["fact_set_hash"]


def test_context_edit_rejects_fact_outside_artifact():
    from app.core.exceptions import AppException
    from app.modules.knowledge.schemas import SourceContextEditRequest
    from app.modules.knowledge.services.source_context import apply_context_edits

    artifact = build_source_artifact("text", 1, {})
    request = SourceContextEditRequest(expected_fact_set_hash=artifact["fact_set_hash"], reason="Đối chiếu nguồn",
                                      facts=[{"fact_id": "outside", "year": 2024}])
    with pytest.raises(AppException) as error:
        apply_context_edits(artifact, request, "actor_fixture")
    assert error.value.code == "FACT_CONTEXT_NOT_FOUND"


@pytest.mark.asyncio
async def test_real_db_context_revision_keeps_serving_pointer_and_rejects_stale_edit():
    import uuid
    from types import SimpleNamespace

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.core.config import settings
    from app.core.exceptions import AppException
    from app.modules.knowledge.models import (
        KnowledgeBinding,
        KnowledgeCollection,
        KnowledgeSourceRevision,
    )
    from app.modules.knowledge.schemas import SourceContextEditRequest
    from app.modules.knowledge.services.source_context import create_context_revision
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service

    scope = f"test387_{uuid.uuid4().hex[:10]}"
    actor = SimpleNamespace(tenant_id=scope, workspace_id=scope, actor_id=scope)
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                    collection = KnowledgeCollection(name="Context fixture", module_code=scope, tenant_id=scope, workspace_id=scope)
                    db.add(collection)
                    await db.flush()
                    binding = KnowledgeBinding(collection_id=collection.id, tenant_id=scope, workspace_id=scope, status="active")
                    db.add(binding)
                    await db.flush()
                    markdown = "\n\n".join(["Nội dung văn bản dùng kiểm chứng ngữ cảnh và đối chiếu bằng chứng nguồn." for _ in range(30)])
                    markdown += "\n\n| Ngành | Điểm chuẩn 2023 |\n| --- | --- |\n| Một ngành học | 15 |"
                    artifact = build_source_artifact(markdown, 1, {})
                    original = KnowledgeSourceRevision(binding_id=binding.id, revision_no=1, origin_document_id="fixture",
                        origin_file_hash=scope, snapshot_storage_path="fixture", snapshot_metadata={"file_name": "fixture2026.pdf"},
                        canonical_markdown=markdown, canonical_hash=artifact["content_hash"], status="ready",
                        page_manifest=[{"page": 1}], parse_provenance={"structured_artifact": artifact})
                    db.add(original)
                    await db.flush()
                    binding.active_source_revision_id = original.id
                    serving_pointer = binding.active_index_revision_id
                    await db.commit()
                    request = SourceContextEditRequest(expected_fact_set_hash=artifact["fact_set_hash"], reason="Đối chiếu ảnh trang gốc",
                        facts=[{"fact_id": artifact["facts"][0]["id"], "year": 2024}])
                    draft = await create_context_revision(db, collection.id, binding.id, original.id, request, actor)
                    await db.refresh(binding)
                    await db.refresh(original)
                    assert draft.id != original.id and draft.status == "review_required"
                    assert binding.active_source_revision_id == original.id
                    assert binding.active_index_revision_id == serving_pointer
                    assert original.parse_provenance["structured_artifact"]["fact_set_hash"] == artifact["fact_set_hash"]
                    with pytest.raises(AppException) as stale:
                        await create_context_revision(db, collection.id, binding.id, original.id, request, actor)
                    assert stale.value.code == "SOURCE_CONTEXT_CHANGED"
                    approved = await source_ingestion_service.review_source_revision(db, collection.id, binding.id, draft.id,
                        "approved", "Đã đối chiếu", scope, scope, actor_id=scope)
                    await db.refresh(binding)
                    await db.refresh(approved)
                    assert approved.status == "ready" and binding.active_source_revision_id == draft.id
                    assert binding.active_index_revision_id == serving_pointer
                    assert approved.parse_provenance["structured_artifact"]["facts"][0]["raw_data"]["context_review"]["review"]["actor_id"] == scope
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
