"""Opt-in real PostgreSQL contracts, isolated by an outer rollback."""

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.modules.assistants.knowledge_readiness import count_ready_sources
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.workflows.execution_audit import expire_abandoned_executions
from app.modules.workflows.models import WorkflowExecution
from app.modules.workflows.schemas import WorkflowDagSpec, WorkflowExecuteRequest
from app.modules.workflows.service import workflow_service

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(
    os.getenv("QNU_TEST_PHASE1_DB") != "1", reason="Opt-in PostgreSQL fixture")]


async def test_serving_sources_and_durable_failure_use_real_db():
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    tag = uuid.uuid4().hex[:10]
    try:
        async with engine.connect() as conn:
            outer = await conn.begin()
            try:
                def session_factory():
                    return AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
                async with session_factory() as db:
                    collection = KnowledgeCollection(id=f"test_ready_{tag}", name="TEST readiness", module_code="general")
                    bindings = [KnowledgeBinding(id=f"test_b{i}_{tag}", collection_id=collection.id, status="active") for i in range(2)]
                    db.add_all([collection, *bindings])
                    await db.flush()
                    generation = KnowledgeVectorGeneration(id=f"test_g_{tag}", collection_id=collection.id,
                        embedding_model="test_encoder", provider_id="test_provider", embedding_dimension=8,
                        config_hash=tag, qdrant_collection_name=f"test_vectors_{tag}", status="active")
                    db.add(generation)
                    await db.flush()
                    source = KnowledgeSourceRevision(id=f"test_s_{tag}", binding_id=bindings[0].id,
                        revision_no=1, origin_document_id=f"test_doc_{tag}", origin_file_hash=tag,
                        snapshot_storage_path=f"test/{tag}", canonical_hash=tag, canonical_markdown="TEST evidence",
                        status="ready", parse_provenance={"structured_artifact": {"content_hash": tag,
                            "issues": [], "review": {"status": "approved"}}})
                    index = KnowledgeIndexRevision(id=f"test_i_{tag}", binding_id=bindings[0].id,
                        vector_generation_id=generation.id,
                        source_revision_v2_id=source.id, revision_no=1, status="active", chunk_count=1,
                        parity_report={"parity_passed": True})
                    db.add(source)
                    await db.flush()
                    db.add(index)
                    await db.flush()
                    bindings[0].active_index_revision_id = index.id
                    await db.flush()
                    # Only one published source; the second draft does not block or count.
                    assert await count_ready_sources(db, collection) == 1
                    index.parity_report = {"parity_passed": False}
                    await db.flush()
                    with pytest.raises(Exception, match="đối soát"):
                        await count_ready_sources(db, collection)
                    await db.commit()
                    spec = WorkflowDagSpec(entry_node_id="in", nodes=[])
                    with (patch.object(workflow_service, "get_workflow_spec", AsyncMock(return_value=spec)),
                          patch("app.modules.workflows.service.dag_engine.execute", AsyncMock(side_effect=RuntimeError("fixture failure"))),
                          patch("app.modules.workflows.execution_audit.AsyncSessionFactory", session_factory),
                          pytest.raises(RuntimeError, match="fixture failure")):
                        await workflow_service.execute(db, WorkflowExecuteRequest(workflow_id=f"test_wf_{tag}", inputs={}))
                    record = (await db.execute(select(WorkflowExecution).where(
                        WorkflowExecution.workflow_id == f"test_wf_{tag}"))).scalar_one()
                    await db.refresh(record)
                    assert record.status == "failed" and record.completed_at
                    assert record.outputs["failure_stage"] == "engine"
                    expired = WorkflowExecution(id=str(uuid.uuid4()), workflow_id=f"test_expired_{tag}",
                                                status="running", runtime_profile={"execution_deadline": 1})
                    paused = WorkflowExecution(id=str(uuid.uuid4()), workflow_id=f"test_paused_{tag}",
                                               status="paused_for_approval", runtime_profile={"execution_deadline": 1})
                    db.add_all([expired, paused])
                    await db.flush()
                    assert await expire_abandoned_executions(db) >= 1
                    await db.refresh(expired)
                    await db.refresh(paused)
                    assert expired.status == "failed"
                    assert paused.status == "paused_for_approval"
            finally:
                await outer.rollback()
    finally:
        await engine.dispose()
