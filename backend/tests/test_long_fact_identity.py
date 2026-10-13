"""Regression coverage for lossless long facts and failed index-job finalization."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine
from app.modules.knowledge.models import KnowledgeCollection, KnowledgeFact
from app.modules.knowledge.services.fact_identity import build_fact_identity


def test_long_fact_keeps_full_text_and_bounded_collision_resistant_label():
    shared = "Nội dung điều kiện tuyển sinh " * 30
    first = build_fact_identity(f"{shared}phương án thứ nhất", raw_data={"table_id": "t1", "row_index": 1})
    second = build_fact_identity(f"{shared}phương án thứ hai", raw_data={"table_id": "t1", "row_index": 2})

    assert len(first.entity_text) > 512
    assert len(first.entity_label) <= 512
    assert first.entity_text.endswith("phương án thứ nhất")
    assert first.entity_key != second.entity_key
    assert first.entity_label != second.entity_label


def test_knowledge_fact_legacy_constructor_populates_long_text_contract():
    full_text = "Đối tượng áp dụng " * 80
    fact = KnowledgeFact(
        collection_id="col",
        entity_name=full_text,
        entity_type="table_row",
        attribute_name="Điều kiện",
        attribute_value="Có",
        raw_data={"page_number": 2, "table_id": "table_2", "row_index": 4},
    )

    assert fact.entity_name == fact.entity_text
    assert len(fact.entity_text) > 512
    assert len(fact.entity_label) <= 512
    assert fact.entity_key.startswith("fact_")


@pytest.mark.asyncio
async def test_long_fact_round_trips_through_postgresql_without_truncation():
    collection_id = f"col_long_{uuid4().hex[:12]}"
    full_text = "Quy định và đối tượng áp dụng " * 100

    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            async with AsyncSession(bind=connection) as db:
                db.add(
                    KnowledgeCollection(
                        id=collection_id,
                        name="Long fact regression",
                        module_code="test",
                    )
                )
                fact = KnowledgeFact(
                    collection_id=collection_id,
                    entity_name=full_text,
                    entity_type="table_row",
                    attribute_name="Điều kiện",
                    attribute_value="Áp dụng",
                    raw_data={"table_id": "long_table", "row_index": 1},
                )
                db.add(fact)
                await db.flush()
                stored = await db.scalar(select(KnowledgeFact).where(KnowledgeFact.id == fact.id))
                assert stored is not None
                assert stored.entity_text == fact.entity_text
                assert len(stored.entity_text) > 512
        finally:
            await transaction.rollback()


@pytest.mark.asyncio
async def test_index_worker_rolls_back_and_reloads_before_marking_failed():
    from app.modules.knowledge.services.vector_generation_service import vector_generation_service
    from app.workers import tasks

    db = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = db
    job = SimpleNamespace(
        id="job_long_fact",
        collection_id="col",
        payload={
            "binding_id": "binding",
            "source_revision_id": "source_revision",
            "generation_id": "generation",
        },
    )
    fresh_job = SimpleNamespace(**job.__dict__)
    events: list[str] = []
    db.rollback.side_effect = lambda: events.append("rollback")

    async def load_job(*_args):
        events.append("reload")
        return job if events.count("reload") == 1 else fresh_job

    async def set_job(_db, selected_job, status, **_kwargs):
        events.append(f"set:{status}:{'fresh' if selected_job is fresh_job else 'original'}")
        return True

    with (
        patch.object(tasks, "AsyncSessionFactory", MagicMock(return_value=cm)),
        patch.object(tasks, "_load_job", AsyncMock(side_effect=load_job)),
        patch.object(tasks, "_check_pre_execution_cancelled", AsyncMock(return_value=False)),
        patch.object(tasks, "_is_cancelled", AsyncMock(return_value=False)),
        patch.object(tasks, "_set_job", AsyncMock(side_effect=set_job)),
        patch.object(
            vector_generation_service,
            "build_generation_for_source",
            AsyncMock(side_effect=ValueError("fact is too long")),
        ),
        pytest.raises(ValueError, match="fact is too long"),
    ):
        await tasks.task_knowledge_index_build({}, job.id)

    assert events.index("rollback") < events.index("set:failed:fresh")
    db.rollback.assert_awaited_once()
