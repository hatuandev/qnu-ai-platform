"""Source-backed controls and OPEN regressions; no production repair in phase 1.

Excerpt copied from the fresh published canonical source (origin PDF SHA-256
236ab3573d6d683a760ed227512022d6c21a03ba5c147c32d4ed7b042f7c6d45),
visually checked on physical pages 1/2. Repeated headers are the parser's
projection, not printed headers on physical page 2. Native text omits the
visible notice number/date; do not fabricate them inside the source excerpt.

Failures ran RED in phase 1. Stages 2/3/4 resolve column role/routing/status.
No DB, models, network, or mocked service output.
"""

from pathlib import Path

import pytest

from app.modules.knowledge.normalization.retrieval_units import build_unit_manifest, unit_chunks
from app.modules.knowledge.services.source_artifact import build_source_artifact, cell_context
from app.modules.knowledge.services.temporal_metadata import extract_temporal_metadata
from app.modules.rag.service import is_refusal_answer
from app.modules.rag.temporal_answer import is_temporal_table_question

EXCERPT = (Path(__file__).parent / "fixtures/rag_floor_121_excerpt.md").read_text(encoding="utf-8")
METHODS = ["Phương thức xét điểm thi TN. THPT", "Phương thức xét kết quả học tập THPT",
           "Phương thức xét điểm thi ĐGNL ĐHQG TPHCM", "Phương thức xét điểm thi ĐGNL ĐHSP HN"]
CASES = [("7140114", "Quản lý giáo dục", 1, ["15", "18", "600", "15"]),
         ("7140209", "Sư phạm Toán học", 2, ["20", "–", "–", "20"])]


@pytest.mark.parametrize("code,name,page,values", CASES)
def test_source_rows_preserve_original_method_values(code, name, page, values):
    artifact = build_source_artifact(EXCERPT, 2, {})
    facts = [fact for fact in artifact["facts"] if fact["raw_data"]["entity_code"] == code]
    assert {fact["entity_name"] for fact in facts} == {name}
    assert {fact["raw_data"]["page_number"] for fact in facts} == {page}
    assert {fact["attribute_name"]: fact["attribute_value"] for fact in facts
            if fact["attribute_name"] in METHODS} == dict(zip(METHODS, values, strict=True))
    assert artifact["issues"] == []


@pytest.mark.parametrize("code,name,page,values", CASES)
def test_index_projection_keeps_row_and_method_headers(code, name, page, values):
    manifest = build_unit_manifest(EXCERPT)
    chunks = unit_chunks(manifest)
    rows = [chunk for chunk in chunks if code in chunk["content"]]
    assert len(rows) == 1
    assert rows[0]["page_number"] == page
    assert all(method in rows[0]["content"] for method in METHODS)
    unit = rows[0]["metadata"]["source_unit"]
    assert EXCERPT[unit["start"]:unit["end"]] == unit["text"]
    assert "| " + " | ".join(values) + " |" in unit["text"]


def test_missing_native_date_and_unknown_cell_year_are_not_invented():
    metadata = extract_temporal_metadata(EXCERPT)
    assert metadata["issued_date"]["value"] is None
    artifact = build_source_artifact(EXCERPT, 2, {})
    assert all(fact["raw_data"]["temporal_context"]["year"] is None for fact in artifact["facts"])


@pytest.mark.parametrize("name", ["Quản lý giáo dục", "Sư phạm Toán học"])
def test_floor_question_reaches_temporal_numeric_routing(name):
    assert is_temporal_table_question(f"Điểm sàn ngành {name} năm 2026 là bao nhiêu?", "admissions")


def test_numeric_score_column_is_not_a_method_identifier():
    assert cell_context(METHODS[1])["attribute_code"] != "admission_method"


def test_non_answer_remains_non_answer_even_with_related_citations():
    assert is_refusal_answer("Không tìm thấy thông tin điểm sàn cho năm được hỏi.", has_evidence=True)
