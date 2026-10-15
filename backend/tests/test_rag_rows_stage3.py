"""Exact source rows survive retrieval; context never changes source/year/value."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest, unit_chunks
from app.modules.knowledge.services.source_artifact import build_source_artifact

EXCERPT = (Path(__file__).parent / "fixtures/rag_floor_121_excerpt.md").read_text(encoding="utf-8")


def fixture_source(markdown=EXCERPT, suffix="a"):
    # The excerpt omits intermediate rows: add a synthetic ordinal control so
    # cross-page linkage is justified structurally, not inferred across a gap.
    markdown = markdown.replace("\n\n<!-- Trang 2 -->", "\n| 5 | 7140206 | Other Entity | 19 | – | – | 19 | C |\n\n<!-- Trang 2 -->")
    artifact = build_source_artifact(markdown, 2, {})
    manifest = resolve_unit_manifest(markdown, artifact)
    source = SimpleNamespace(id="source_" + suffix, canonical_markdown=markdown,
        canonical_hash=manifest.canonical_hash, parse_provenance={"structured_artifact": artifact},
        snapshot_metadata={"title": "Source " + suffix})
    index = SimpleNamespace(id="index_" + suffix, parity_report={"parity_passed": True,
        "unit_manifest_hash": artifact["unit_manifest_hash"]}, chunk_count=10)
    binding = SimpleNamespace(id="binding_" + suffix)
    chunks = [SimpleNamespace(id=f"chunk_{suffix}_{c['index']}", content=c["content"],
        page_number=c["page_number"], section=c["section"], chunk_metadata=c["metadata"],
        binding_id=binding.id, index_revision_id=index.id) for c in unit_chunks(manifest)]
    return source, index, binding, chunks


@pytest.mark.parametrize("name,code,values", [
    ("Quản lý giáo dục", "7140114", "| 15 | 18 | 600 | 15 |"),
    ("Sư phạm Toán học", "7140209", "| 20 | – | – | 20 |"),
])
def test_exact_entity_row_retains_all_methods_and_raw_quote(name, code, values):
    from app.modules.rag.source_rows import source_rows

    source, index, binding, chunks = fixture_source()
    rows = source_rows(source, index, binding, chunks, f"Điểm sàn ngành {name} năm 2026?")
    assert len(rows) == 1
    assert code in rows[0].content and values in rows[0].content
    assert rows[0].metadata["source_revision_id"] == source.id
    assert any("năm 2026" in context["text"] for context in rows[0].metadata["row_context"])
    assert rows[0].metadata["data_years"] == []


def test_subject_combination_mentions_do_not_match_another_entity():
    from app.modules.rag.source_rows import source_rows

    markdown = EXCERPT.replace("Quản lý giáo<br>dục", "Entity Other").replace("(Văn, Sử, Địa)", "(Quản lý giáo dục)")
    assert source_rows(*fixture_source(markdown), "Điểm sàn Quản lý giáo dục 2026?") == []


def test_generic_unigram_is_not_an_entity_anchor():
    from app.modules.rag.source_rows import source_rows

    assert source_rows(*fixture_source(), "Điểm thi năm 2026?") == []


def test_modified_published_source_fails_closed():
    from app.modules.rag.source_rows import source_rows

    source, index, binding, chunks = fixture_source()
    source.canonical_markdown += "tampered"
    with pytest.raises(AppException) as error:
        source_rows(source, index, binding, chunks, "Quản lý giáo dục 2026?")
    assert error.value.code == "SOURCE_ROW_INVALID"


@pytest.mark.asyncio
async def test_row_database_failure_is_not_an_empty_answer():
    from app.modules.rag.schemas import RetrievalSnapshot
    from app.modules.rag.source_rows import load_row_anchors

    db = AsyncMock()
    db.execute.side_effect = ConnectionError("DB down")
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="c", tenant_id="t", workspace_id="w",
                                 binding_revisions={"binding": "index"})
    with pytest.raises(AppException) as error:
        await load_row_anchors(db, snapshot, "Điểm sàn ngành Sư phạm Toán học năm 2026?")
    assert error.value.code == "SOURCE_ROW_UNAVAILABLE"


def test_reserved_row_and_linked_notes_survive_top_k_without_duplicate_citations():
    from app.modules.rag.source_rows import merge_row_anchors, source_rows

    markdown = EXCERPT + "\n\n1. Điều kiện bổ sung.\n\nKý hiệu –: không xét tuyển."
    rows = source_rows(*fixture_source(markdown), "Điểm sàn Sư phạm Toán học 2026?")
    candidates = merge_row_anchors([], rows, 5)
    assert any("7140209" in candidate.content for candidate in candidates)
    assert any("Điều kiện bổ sung" in candidate.content for candidate in candidates)
    assert len({candidate.chunk_id for candidate in candidates}) == len(candidates)
    from app.modules.rag.citation_guard import citation_guard

    for candidate, citation in zip(candidates, citation_guard.build_citations(candidates), strict=True):
        raw = candidate.metadata["source_unit"]
        assert citation.quote.rstrip(".") in raw["text"]
        assert citation.source_pages == candidate.metadata["source_pages"]
        assert raw["text"] in fixture_source(markdown)[0].canonical_markdown


def test_empty_anchor_results_preserve_configured_reranker_output():
    from app.modules.rag.fusion import FusionCandidate
    from app.modules.rag.source_rows import merge_row_anchors

    candidates = [FusionCandidate(str(i), "d", "text", 0.1) for i in range(20)]
    assert merge_row_anchors(candidates, [], 5) is candidates


@pytest.mark.asyncio
async def test_real_postgres_entity_and_year_selection_precedes_limit():
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.core.config import settings
    from app.modules.knowledge.models import KnowledgeBinding, KnowledgeCollection, KnowledgeFact
    from app.modules.rag.facts import fact_layer

    scope = "test468_" + uuid.uuid4().hex[:12]
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False) as db:
                    collection = KnowledgeCollection(name=scope, module_code=scope, tenant_id=scope, workspace_id=scope)
                    db.add(collection)
                    await db.flush()
                    binding = KnowledgeBinding(collection_id=collection.id, tenant_id=scope, workspace_id=scope, status="active")
                    db.add(binding)
                    await db.flush()
                    for number, entity, year in [(i, "Other Entity", None) for i in range(20)] + [
                        (21, "Target Entity", None), (22, "Target Entity", 2025), (23, "Target Entity", 2026)]:
                        db.add(KnowledgeFact(id=f"{scope}_{number:02d}", collection_id=collection.id,
                            binding_id=binding.id, index_revision_id=scope, entity_name=entity,
                            entity_type="table_row", attribute_name="Metric label", attribute_value=str(number),
                            applicability_year=year))
                    await db.flush()
                    result = await fact_layer.lookup_facts(db, collection.id, keywords=["Metric label"],
                        target_entities=["Target Entity"], requested_years=[2026], active_index_revision_ids={scope},
                        tenant_id=scope, workspace_id=scope, limit=1)
                    assert len(result) == 1 and result[0].attribute_value == "23"
                    assert await fact_layer.lookup_facts(db, collection.id, keywords=["Metric label"],
                        target_entities=["Target Entity"], tenant_id=scope + "_other", limit=1) == []
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_untyped_metric_does_not_promote_all_same_entity_facts_over_the_row():
    from unittest.mock import patch

    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
    from app.modules.rag.service import RagService
    from app.modules.rag.source_rows import source_rows

    rows = source_rows(*fixture_source(), "Điểm sàn Quản lý giáo dục 2026?")
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="c", tenant_id="t", workspace_id="w", binding_revisions={"binding_a": "index_a"})
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={})  # Do not enable evidence policy.
    unrelated_metric = SimpleNamespace(id="fee", entity_name="Quản lý giáo dục", attribute_name="Phí", attribute_value="999999", raw_data={})
    with patch("app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot)), \
         patch("app.modules.rag.service.fact_layer.lookup_facts", AsyncMock(return_value=[unrelated_metric])), \
         patch("app.modules.rag.service.hybrid_retriever.retrieve", AsyncMock(return_value=[])), \
         patch("app.modules.rag.service.hybrid_retriever.expand_with_neighbors", AsyncMock(return_value={})), \
         patch("app.modules.rag.service.load_row_anchors", AsyncMock(return_value=rows)), \
         patch("app.modules.rag.service.answer_from_rows", AsyncMock(return_value=None)), \
         patch.object(RagService, "_generate_answer_with_fallback", AsyncMock(return_value="15 / 18 / 600 / 15")) as generation:
        await RagService().ask(db, AskRequest(question="Điểm sàn Quản lý giáo dục 2026?", collection_id="c", module_code="admissions"))
    prompt = generation.call_args.kwargs["llm_messages"][-1].content
    assert "999999" not in prompt
    assert "| 15 | 18 | 600 | 15 |" in prompt
    assert "Ngưỡng bảo đảm chất lượng đầu vào" in prompt
