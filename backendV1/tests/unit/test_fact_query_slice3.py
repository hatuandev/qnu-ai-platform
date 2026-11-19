"""Unit tests for Slice 3: kb_index_table_facts schema, migration & scoped query_facts."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.facts import project_table
from qnu.domains.knowledge.index.models import IndexTableFact
from qnu.domains.rag.answer.fact_query import (
    FactFilter,
    FactQueryRequest,
    ScopedTableSchema,
    execute_fact_query,
    get_table_schemas,
    parse_numeric_value,
    rows_for_projection,
)
from qnu.platform.errors import AppException
from qnu.platform.ownership import V1_TABLES
from qnu.platform.schema import SCHEMA_HEAD
from tests.unit.test_universal_facts_slice1 import _cell


def _sample_schema(projected) -> ScopedTableSchema:
    return ScopedTableSchema(
        table_id=projected.table_id,
        source_table_citation=projected.source_table_citation,
        table_title=projected.title,
        index_run_id="idx_run_1",
        collection_id="col_1",
        document_id="cdoc_1",
        version_id="cver_1",
        publication_decision_id="pdec_1",
        has_header=projected.has_header,
        keep_whole_in_chunk=projected.keep_whole_in_chunk,
        column_keys=list(projected.column_keys),
        data_years=list(projected.data_years),
        data_row_count=projected.table_schema().data_row_count,
        scoped_notes=list(projected.scoped_notes),
    )


def test_orm_model_indexes_cascades_and_schema_registration():
    table = IndexTableFact.__table__
    assert table.name == "kb_index_table_facts"
    assert "kb_index_table_facts" in V1_TABLES
    assert SCHEMA_HEAD == "0036_kb_index_table_facts"

    indexes = {idx.name: idx for idx in table.indexes}
    assert "ix_kb_index_table_facts_scope" in indexes
    scope_cols = [c.name for c in indexes["ix_kb_index_table_facts_scope"].columns]
    assert scope_cols == ["workspace_id", "index_run_id", "table_id", "data_year", "row_kind"]

    assert "ix_kb_index_table_facts_attributes_gin" in indexes
    gin_idx = indexes["ix_kb_index_table_facts_attributes_gin"]
    assert [c.name for c in gin_idx.columns] == ["attributes"]
    assert gin_idx.dialect_options["postgresql"]["using"] == "gin"

    fk_cascades = {fk.name: fk.ondelete for fk in table.foreign_key_constraints}
    assert fk_cascades["fk_index_table_fact_run"] == "CASCADE"
    assert fk_cascades["fk_index_table_fact_input"] == "CASCADE"


def test_invalid_column_name_rejected_against_real_schema():
    table = {
        "row_count": 2,
        "column_count": 3,
        "rows": [
            [
                _cell("Mã ngành", header=True, evidence_id="h0"),
                _cell("Tên ngành", header=True, evidence_id="h1"),
                _cell("Chỉ tiêu", header=True, evidence_id="h2"),
            ],
            [_cell("0001", evidence_id="r1_0"), _cell("Toán", evidence_id="r1_1"), _cell("100", evidence_id="r1_2")],
        ],
    }
    projected = project_table(table, table_id="tbl_1", source_table_citation="ocr_1:ev_p001_b001")
    schema = _sample_schema(projected)

    with pytest.raises(AppException) as exc:
        execute_fact_query(
            projected.facts,
            schema,
            FactQueryRequest(
                table_id="tbl_1",
                aggregation="sum",
                target_column="chi_tieu_doan_sai",
            ),
        )
    assert exc.value.code == "fact_query_invalid_column"
    assert exc.value.status_code == 422
    assert "Chỉ tiêu" in exc.value.detail


def test_aggregations_only_use_data_rows_and_never_coerce_special_value_kinds_to_zero():
    table = {
        "row_count": 10,
        "column_count": 4,
        "rows": [
            [
                _cell("Mã", header=True, evidence_id="h0"),
                _cell("Tên ngành", header=True, evidence_id="h1"),
                _cell("Chỉ tiêu", header=True, evidence_id="h2"),
                _cell("Tổ hợp xét tuyển", header=True, evidence_id="h3"),
            ],
            [_cell("I. KHỐI SƯ PHẠM", col_span=4, evidence_id="g1")],
            [_cell("0001", evidence_id="r2_0"), _cell("Sư phạm Toán", evidence_id="r2_1"), _cell("120", evidence_id="r2_2"), _cell("(Toán, Lý, Hóa)", evidence_id="r2_3")],
            [_cell("0002", evidence_id="r3_0"), _cell("Sư phạm Văn", evidence_id="r3_1"), _cell("80", evidence_id="r3_2"), _cell("(Văn, Toán, Địa)", evidence_id="r3_3")],
            [_cell("0003", evidence_id="r4_0"), _cell("Sư phạm Sử", evidence_id="r4_1"), _cell("0", evidence_id="r4_2"), _cell("(Toán, Văn, Địa)", evidence_id="r4_3")],
            [_cell("0004", evidence_id="r5_0"), _cell("Sư phạm Địa", evidence_id="r5_1"), _cell("", evidence_id="r5_2"), _cell("(Văn, Sử, Địa)", evidence_id="r5_3")],
            [_cell("0005", evidence_id="r6_0"), _cell("Sư phạm Lý", evidence_id="r6_1"), _cell("Chưa công bố", evidence_id="r6_2"), _cell("(Toán, Lý, Anh)", evidence_id="r6_3")],
            [_cell("0006", evidence_id="r7_0"), _cell("Sư phạm Hóa", evidence_id="r7_1"), _cell("–", evidence_id="r7_2"), _cell("(Toán, Hóa, Sinh)", evidence_id="r7_3")],
            [_cell("0007", evidence_id="r8_0"), _cell("Sư phạm Sinh", evidence_id="r8_1"), _cell("/", evidence_id="r8_2"), _cell("(Toán, Hóa, Sinh)", evidence_id="r8_3")],
            [_cell("Tổng cộng", col_span=2, evidence_id="s9_0"), _cell("200", evidence_id="s9_2"), _cell("", evidence_id="s9_3")],
        ],
    }
    projected = project_table(
        table,
        table_id="tbl_agg",
        source_table_citation="ocr_5:ev_p002_b001",
        title="Bảng chỉ tiêu tổng hợp",
        defined_symbols={"–"},
    )
    schema = _sample_schema(projected)

    # 1. COUNT: only counts the 7 data rows (excludes group_header and summary)
    res_count = execute_fact_query(
        projected.facts,
        schema,
        FactQueryRequest(table_id="tbl_agg", aggregation="count"),
    )
    assert res_count.total_matched_rows == 7
    assert res_count.numeric_result == "7"

    # 2. SUM: 120 + 80 + 0 = 200 (does NOT double-count summary 200; excludes 4 special kinds)
    res_sum = execute_fact_query(
        projected.facts,
        schema,
        FactQueryRequest(table_id="tbl_agg", aggregation="sum", target_column="Chỉ tiêu"),
    )
    assert res_sum.numeric_result == "200"
    assert res_sum.included_numeric_count == 3
    assert res_sum.excluded_by_value_kind == {
        "empty_cell": 1,
        "not_published": 1,
        "defined_symbol": 1,
        "undefined_symbol": 1,
    }
    assert "ocr_5:r2_2" in res_sum.source_cell_refs
    assert "ocr_5:s9_2" not in res_sum.source_cell_refs

    # 3. MIN excluding the explicit numeric_zero row must be 80, NEVER 0 from empty_cell or "/"
    res_min_gt0 = execute_fact_query(
        projected.facts,
        schema,
        FactQueryRequest(
            table_id="tbl_agg",
            aggregation="min",
            target_column="Chỉ tiêu",
            filters=[FactFilter(column="Chỉ tiêu", op="gt", value=0)],
        ),
    )
    assert res_min_gt0.numeric_result == "80"
    assert res_min_gt0.included_numeric_count == 2

    # 4. Numeric filter <= 10 matches ONLY numeric_zero ("0"), NEVER empty_cell / "/" / "–"
    res_lte = execute_fact_query(
        projected.facts,
        schema,
        FactQueryRequest(
            table_id="tbl_agg",
            aggregation="list",
            filters=[FactFilter(column="Chỉ tiêu", op="lte", value=10)],
        ),
    )
    assert [r.subject_code for r in res_lte.matched_rows] == ["0003"]

    # 5. Unordered set_contains filter matches both (Văn, Toán, Địa) and (Toán, Văn, Địa)
    res_set = execute_fact_query(
        projected.facts,
        schema,
        FactQueryRequest(
            table_id="tbl_agg",
            aggregation="list",
            filters=[FactFilter(column="Tổ hợp xét tuyển", op="set_contains", value=["Toán", "Văn", "Địa"])],
        ),
    )
    assert [r.subject_name for r in res_set.matched_rows] == ["Sư phạm Văn", "Sư phạm Sử"]


def test_set_contains_never_mixes_subjects_across_distinct_combinations_in_same_cell():
    table = {
        "row_count": 4,
        "column_count": 3,
        "rows": [
            [
                _cell("Mã", header=True, evidence_id="h0"),
                _cell("Tên ngành", header=True, evidence_id="h1"),
                _cell("Tổ hợp xét tuyển", header=True, evidence_id="h2"),
            ],
            # Two separate combinations separated by semicolon: Toán is in #1, Văn & Địa are in #2
            [
                _cell("0001", evidence_id="r1_0"),
                _cell("Ngành A", evidence_id="r1_1"),
                _cell("(Toán, Lý, Hóa); (Văn, Sử, Địa)", evidence_id="r1_2"),
            ],
            # Two separate combinations on same line separated by space/comma outside parentheses
            [
                _cell("0002", evidence_id="r2_0"),
                _cell("Ngành B", evidence_id="r2_1"),
                _cell("A00 (Toán, Lý, Hóa), C00 (Văn, Sử, Địa)", evidence_id="r2_2"),
            ],
            # True match: (Địa, Toán, Văn) is a single combination
            [
                _cell("0003", evidence_id="r3_0"),
                _cell("Ngành C", evidence_id="r3_1"),
                _cell("(Toán, Lý, Anh); (Địa, Toán, Văn)", evidence_id="r3_2"),
            ],
        ],
    }
    projected = project_table(table, table_id="tbl_combo", source_table_citation="ocr_6:ev_p001_b001")
    schema = _sample_schema(projected)

    res = execute_fact_query(
        projected.facts,
        schema,
        FactQueryRequest(
            table_id="tbl_combo",
            aggregation="list",
            filters=[FactFilter(column="Tổ hợp xét tuyển", op="set_contains", value=["Toán", "Văn", "Địa"])],
        ),
    )
    # Must match ONLY Ngành C — never mix Toán from (Toán, Lý, Hóa) with Văn, Địa from (Văn, Sử, Địa)
    assert [r.subject_name for r in res.matched_rows] == ["Ngành C"]

    # Explicit case: "(Toán, Văn, Anh), (Toán, Lý, Hóa)" MUST NOT match (Toán, Lý, Anh)
    table2 = {
        "row_count": 2,
        "column_count": 3,
        "rows": [
            [
                _cell("Mã", header=True, evidence_id="h0"),
                _cell("Tên ngành", header=True, evidence_id="h1"),
                _cell("Tổ hợp xét tuyển", header=True, evidence_id="h2"),
            ],
            [
                _cell("0010", evidence_id="r1_0"),
                _cell("Ngành D", evidence_id="r1_1"),
                _cell("(Toán, Văn, Anh), (Toán, Lý, Hóa)", evidence_id="r1_2"),
            ],
        ],
    }
    projected2 = project_table(table2, table_id="tbl_combo2", source_table_citation="ocr_6:ev_p002_b001")
    schema2 = _sample_schema(projected2)
    res2 = execute_fact_query(
        projected2.facts,
        schema2,
        FactQueryRequest(
            table_id="tbl_combo2",
            aggregation="list",
            filters=[
                FactFilter(
                    column="Tổ hợp xét tuyển",
                    op="set_contains",
                    value=["Toán", "Lý", "Anh"],
                )
            ],
        ),
    )
    assert res2.matched_rows == []
    assert res2.total_matched_rows == 0


def test_parse_numeric_value_handles_vn_and_intl_formats():
    assert str(parse_numeric_value("5.173")) == "5173"
    assert str(parse_numeric_value("25,85")) == "25.85"
    assert str(parse_numeric_value("1.250,5")) == "1250.5"
    assert str(parse_numeric_value("0,0")) == "0.0"
    assert parse_numeric_value("AM-0007") is None
    assert parse_numeric_value("/") is None


@pytest.mark.asyncio
async def test_get_table_schemas_enforces_workspace_access_and_builds_orm_rows():
    actor = AuthActor(
        subject="user_1",
        username="user_1",
        email="u@qnu.edu.vn",
        display_name="User",
        roles=frozenset({"member"}),
    )
    fake_db = AsyncMock()
    # Active runs query returns empty -> returns [] after verifying workspace access
    fake_result = AsyncMock()
    fake_result.all = list
    fake_db.execute.return_value = fake_result

    with patch(
        "qnu.domains.rag.answer.fact_query.resolve_workspace_access", new_callable=AsyncMock
    ) as mock_access:
        schemas = await get_table_schemas(fake_db, actor, "ws_1", ["col_1"])
        assert schemas == []
        mock_access.assert_awaited_once_with(fake_db, actor, "ws_1")

    # Verify rows_for_projection produces valid IndexTableFact ORM instances
    table = {
        "row_count": 2,
        "column_count": 2,
        "rows": [
            [_cell("Mã", header=True, evidence_id="h0"), _cell("Tên", header=True, evidence_id="h1")],
            [_cell("0012", evidence_id="r1_0"), _cell("Toán", evidence_id="r1_1")],
        ],
    }
    projected = project_table(table, table_id="tbl_orm", source_table_citation="ocr_1:ev_p001_b001")
    counter = iter(["ft_1", "ft_2"])
    orm_rows = rows_for_projection(
        projected,
        input_id="inp_1",
        index_run_id="idx_1",
        workspace_id="ws_1",
        collection_id="col_1",
        document_id="cdoc_1",
        version_id="cver_1",
        publication_decision_id="pdec_1",
        id_factory=lambda: next(counter),
    )
    assert len(orm_rows) == 1
    assert orm_rows[0].table_id == "tbl_orm"
    assert orm_rows[0].subject_code == "0012"
    assert orm_rows[0].column_keys == ["Mã", "Tên"]
