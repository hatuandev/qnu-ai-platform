"""Integration test on real PostgreSQL for Slice 3B:
publish -> atomic swap kb_index_table_facts -> get_table_schemas() ->
query_facts() -> cells.py::materialize() -> CASCADE cleanup on run delete.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.index.facts import project_table
from qnu.domains.knowledge.index.models import IndexInput, IndexRun, IndexTableFact
from qnu.domains.knowledge.models import KBCollection
from qnu.domains.knowledge.publication.models import (
    CompiledDocument,
    CompiledVersion,
    PublicationDecision,
    PublicationPreview,
)
from qnu.domains.modelops.models import Provider
from qnu.domains.rag.answer.cells import catalog
from qnu.domains.rag.answer.fact_query import (
    FactFilter,
    FactQueryRequest,
    get_table_schemas,
    materialize_fact_query_answer,
    query_facts,
    rows_for_projection,
)
from qnu.domains.rag.answer.schemas import EvidenceSource
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.models import Workspace, WorkspaceMember
from qnu.platform.database import AsyncSessionFactory
from tests.unit.test_universal_facts_slice1 import _cell


def test_universal_facts_full_lifecycle_on_real_postgres(client):
    actor = AuthActor(
        actor_id="admin_facts_test",
        username="admin_facts_test",
        email="admin@qnu.edu.vn",
        display_name="Admin Facts",
        roles=["admin"],
        authenticated=True,
    )
    aref = actor_ref(actor)

    table = {
        "row_count": 8,
        "column_count": 4,
        "rows": [
            [
                _cell("Mã", header=True, evidence_id="ev_h0"),
                _cell("Tên ngành", header=True, evidence_id="ev_h1"),
                _cell("Chỉ tiêu", header=True, evidence_id="ev_h2"),
                _cell("Tổ hợp xét tuyển", header=True, evidence_id="ev_h3"),
            ],
            [_cell("I. KHỐI SƯ PHẠM", col_span=4, evidence_id="ev_g1")],
            [
                _cell("0001", evidence_id="ev_r2_0"),
                _cell("Sư phạm Toán", evidence_id="ev_r2_1"),
                _cell("120", evidence_id="ev_r2_2"),
                _cell("(Toán, Lý, Hóa); (Văn, Sử, Địa)", evidence_id="ev_r2_3"),
            ],
            [
                _cell("0002", evidence_id="ev_r3_0"),
                _cell("Sư phạm Văn", evidence_id="ev_r3_1"),
                _cell("80", evidence_id="ev_r3_2"),
                _cell("(Văn, Toán, Địa)", evidence_id="ev_r3_3"),
            ],
            [
                _cell("0003", evidence_id="ev_r4_0"),
                _cell("Sư phạm Sử", evidence_id="ev_r4_1"),
                _cell("0", evidence_id="ev_r4_2"),
                _cell("(Toán, Văn, Địa)", evidence_id="ev_r4_3"),
            ],
            [
                _cell("0004", evidence_id="ev_r5_0"),
                _cell("Sư phạm Địa", evidence_id="ev_r5_1"),
                _cell("", evidence_id="ev_r5_2"),
                _cell("(Văn, Sử, Địa)", evidence_id="ev_r5_3"),
            ],
            [
                _cell("0005", evidence_id="ev_r6_0"),
                _cell("Sư phạm Lý", evidence_id="ev_r6_1"),
                _cell("/", evidence_id="ev_r6_2"),
                _cell("(Toán, Lý, Anh)", evidence_id="ev_r6_3"),
            ],
            [
                _cell("Tổng cộng", col_span=2, evidence_id="ev_s7_0"),
                _cell("200", evidence_id="ev_s7_2"),
                _cell("", evidence_id="ev_s7_3"),
            ],
        ],
    }

    async def _run() -> None:
        async with AsyncSessionFactory() as db:
            db.add(
                Workspace(
                    id="ws_facts_1",
                    code="ws-facts-1",
                    name="Workspace Facts Test",
                    status="active",
                    created_by=aref,
                )
            )
            await db.flush()
            db.add(
                WorkspaceMember(
                    id="wm_facts_1",
                    workspace_id="ws_facts_1",
                    actor_ref=aref,
                    display_name="Admin Facts",
                    role="admin",
                    status="active",
                )
            )
            db.add(
                KBCollection(
                    id="col_facts_1",
                    workspace_id="ws_facts_1",
                    name="Tuyển sinh 2026",
                    created_by=aref,
                )
            )
            db.add(
                Provider(
                    id="prv_emb_1",
                    name="Test Embed",
                    provider_type="openai_compatible",
                    base_url="http://localhost:9999/v1",
                    model_name="bge-m3",
                    capabilities=["embedding"],
                    is_active=True,
                    created_by=aref,
                )
            )
            await db.flush()

            db.add(
                CompilationRun(
                    id="cmp_facts_1",
                    workspace_id="ws_facts_1",
                    collection_id="col_facts_1",
                    generation=1,
                    status="completed",
                    topic="Tuyển sinh",
                    input_sha256="a" * 64,
                    config={"source_first": True},
                    requested_by=aref,
                    idempotency_key="ik_cmp_1",
                    request_hash="b" * 64,
                )
            )
            db.add(
                CompiledDocument(
                    id="cdoc_facts_1",
                    workspace_id="ws_facts_1",
                    collection_id="col_facts_1",
                    document_key="ts_2026",
                    title="Thông tin TSĐH 2026",
                    created_by=aref,
                )
            )
            await db.flush()

            db.add(
                CompiledVersion(
                    id="cver_facts_1",
                    document_id="cdoc_facts_1",
                    workspace_id="ws_facts_1",
                    collection_id="col_facts_1",
                    compilation_run_id="cmp_facts_1",
                    version_no=1,
                    status="published",
                    state_version=2,
                    input_sha256="a" * 64,
                    draft_sha256="b" * 64,
                    markdown_sha256="c" * 64,
                    bundle_sha256="d" * 64,
                    provenance={},
                    created_by=aref,
                    idempotency_key="ik_cver_1",
                    request_hash="e" * 64,
                )
            )
            await db.flush()

            db.add(
                PublicationPreview(
                    id="pprev_facts_1",
                    version_id="cver_facts_1",
                    document_id="cdoc_facts_1",
                    workspace_id="ws_facts_1",
                    collection_id="col_facts_1",
                    actor_ref=aref,
                    action="publish",
                    reason="Publish test",
                    expected_document_sequence=1,
                    expected_version_sequence=1,
                    bundle_sha256="d" * 64,
                    preview_sha256="f" * 64,
                    expires_at=utcnow(),
                )
            )
            await db.flush()

            db.add(
                PublicationDecision(
                    id="pdec_facts_1",
                    preview_id="pprev_facts_1",
                    version_id="cver_facts_1",
                    document_id="cdoc_facts_1",
                    workspace_id="ws_facts_1",
                    collection_id="col_facts_1",
                    actor_ref=aref,
                    action="publish",
                    reason="Publish test",
                    idempotency_key="ik_pdec_1",
                    request_hash="1" * 64,
                    document_sequence=1,
                    bundle_sha256="d" * 64,
                    before={},
                    after={},
                )
            )
            run = IndexRun(
                id="idx_facts_1",
                workspace_id="ws_facts_1",
                collection_id="col_facts_1",
                generation=1,
                status="running",
                is_active=False,
                provider_id="prv_emb_1",
                dimension=1024,
                vector_collection="qnu_v1_idx_facts_test_1",
                config={},
                input_sha256="2" * 64,
                requested_by=aref,
                idempotency_key="ik_idx_1",
                request_hash="3" * 64,
            )
            db.add(run)
            await db.flush()

            db.add(
                IndexInput(
                    id="iin_facts_1",
                    run_id="idx_facts_1",
                    workspace_id="ws_facts_1",
                    collection_id="col_facts_1",
                    document_id="cdoc_facts_1",
                    version_id="cver_facts_1",
                    publication_decision_id="pdec_facts_1",
                    bundle_sha256="d" * 64,
                    version_state=2,
                )
            )
            await db.flush()

            # 2. Write kb_index_table_facts while IndexRun is still staged (is_active=False)
            projected = project_table(
                table,
                table_id="ocr_1:ev_p004_b001",
                source_table_citation="ocr_1:ev_p004_b001",
                title="Danh mục ngành 2026",
            )
            seq = iter(f"ft_int_{i}" for i in range(100))
            db.add_all(
                rows_for_projection(
                    projected,
                    input_id="iin_facts_1",
                    index_run_id="idx_facts_1",
                    workspace_id="ws_facts_1",
                    collection_id="col_facts_1",
                    document_id="cdoc_facts_1",
                    version_id="cver_facts_1",
                    publication_decision_id="pdec_facts_1",
                    id_factory=lambda: next(seq),
                )
            )
            await db.commit()

            # Atomic swap check: staged run (is_active=False) MUST NOT be visible
            assert await get_table_schemas(db, actor, "ws_facts_1", ["col_facts_1"]) == []

            # Activate index run atomically
            run.status = "completed"
            run.is_active = True
            await db.commit()

            # 3. Step 1: get_table_schemas()
            schemas = await get_table_schemas(db, actor, "ws_facts_1", ["col_facts_1"])
            assert len(schemas) == 1
            assert schemas[0].table_id == "ocr_1:ev_p004_b001"
            assert schemas[0].column_keys == ["Mã", "Tên ngành", "Chỉ tiêu", "Tổ hợp xét tuyển"]
            assert schemas[0].data_row_count == 5

            # 4. Step 2: query_facts() SUM + set_contains
            sum_res = await query_facts(
                db,
                actor,
                "ws_facts_1",
                ["col_facts_1"],
                FactQueryRequest(
                    table_id="ocr_1:ev_p004_b001",
                    aggregation="sum",
                    target_column="Chỉ tiêu",
                ),
            )
            assert sum_res.numeric_result == "200"
            assert sum_res.included_numeric_count == 3
            assert sum_res.excluded_by_value_kind == {"empty_cell": 1, "undefined_symbol": 1}

            combo_res = await query_facts(
                db,
                actor,
                "ws_facts_1",
                ["col_facts_1"],
                FactQueryRequest(
                    table_id="ocr_1:ev_p004_b001",
                    aggregation="list",
                    filters=[
                        FactFilter(
                            column="Tổ hợp xét tuyển",
                            op="set_contains",
                            value=["Toán", "Văn", "Địa"],
                        )
                    ],
                ),
            )
            # Row 0001 has (Toán, Lý, Hóa); (Văn, Sử, Địa) -> MUST NOT match!
            assert [r.subject_name for r in combo_res.matched_rows] == ["Sư phạm Văn", "Sư phạm Sử"]

            # 5. Route through cells.py::materialize()
            all_citations = {
                f"ocr_1:{c['evidence_id']}": {"page_number": 4}
                for row in table["rows"]
                for c in row
                if c.get("evidence_id")
            }
            ev_source = EvidenceSource(
                evidence_id="E1",
                chunk_id="ich_1",
                document_id="cdoc_facts_1",
                version_id="cver_facts_1",
                publication_decision_id="pdec_facts_1",
                score=1.0,
                kind="table",
                text="Danh mục ngành 2026",
                citations=all_citations,
                structure={
                    "source_table_citation": "ocr_1:ev_p004_b001",
                    "original_row_count": table["row_count"],
                    "original_column_count": table["column_count"],
                    "row_indices": list(range(table["row_count"])),
                    "rows": table["rows"],
                },
            )
            cell_catalog = catalog([ev_source], include_names=True)
            materialized = materialize_fact_query_answer(combo_res, [ev_source], cell_catalog)
            assert materialized.status == "answered"
            rendered_texts = [s.text for s in materialized.statements]
            assert "Sư phạm Văn" in rendered_texts
            assert "Sư phạm Sử" in rendered_texts
            assert "Sư phạm Toán" not in rendered_texts

            # 6. Withdraw / Delete IndexRun -> verify purge_graph ownership & ON DELETE CASCADE
            from qnu.domains.lifecycle.purge_graph import COLLECTION_TABLES, SOURCE_TABLES

            assert "kb_index_table_facts" in SOURCE_TABLES
            assert "kb_index_table_facts" in COLLECTION_TABLES
            await db.execute(delete(IndexInput).where(IndexInput.run_id == "idx_facts_1"))
            await db.execute(delete(IndexRun).where(IndexRun.id == "idx_facts_1"))
            await db.commit()

            remaining = await db.scalar(
                select(func.count(IndexTableFact.id)).where(
                    IndexTableFact.index_run_id == "idx_facts_1"
                )
            )
            assert remaining == 0

    client.portal.call(_run)
