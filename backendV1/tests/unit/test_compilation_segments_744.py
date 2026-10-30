"""Segmented compilation keeps every table row and never sends the whole snapshot."""

import copy

import pytest

from qnu.domains.knowledge.compilation import segments as split
from qnu.platform.errors import AppException


def test_trailing_conditions_and_headers_remain_available_across_pages():
    doc = document()
    doc["pages"].append({
        "page_number": 2,
        "status": "ready",
        "blocks": [{
            "evidence_id": "ev_condition",
            "type": "text",
            "text": "Điều kiện bổ sung áp dụng cho các hàng trên.",
            "bbox": [0, 0, 10, 10],
        }],
    })
    units = split.build_units([doc])
    row = next(unit for unit in units if unit.kind == "table_row")
    refs = split.context_refs([doc], [row])
    projected = split.project_documents([doc], split.owned_refs([row]), refs)
    assert any(
        block["evidence_id"] == "ev_condition"
        for page in projected[0]["pages"] for block in page["blocks"]
    )
    assert projected[0]["pages"][0]["blocks"][-1]["table"]["rows"][0][0]["header"]


def test_finalize_rejects_duplicate_ownership():
    docs = [document()]
    plan = split.build_plan(
        index=1, units=split.build_units(docs), documents=docs,
        topic="Tóm tắt", structured=False, total_estimate=2,
    )
    with pytest.raises(AppException) as error:
        split.finalize_plans([plan, plan], docs, "Tóm tắt", capacity=100_000, structured=False)
    assert error.value.code == "compilation_plan_invalid"


def cell(evidence_id: str, text: str, *, header: bool = False) -> dict:
    return {
        "evidence_id": evidence_id,
        "text": text,
        "header": header,
        "row_span": 1,
        "col_span": 1,
    }


def document(*, text: str = "Nội dung nguồn.") -> dict:
    return {
        "ocr_run_id": "ocr_one",
        "canonical_sha256": "1" * 64,
        "manifest_sha256": "2" * 64,
        "identity": {"revision_id": "rev_one"},
        "evidence": {"ev_title": {}, "ev_table": {}},
        "pages": [
            {
                "page_number": 1,
                "status": "ready",
                "blocks": [
                    {
                        "evidence_id": "ev_title",
                        "type": "title",
                        "text": "Bảng ngưỡng",
                        "bbox": [0, 0, 10, 10],
                    },
                    {
                        "evidence_id": "ev_table",
                        "type": "table",
                        "text": text,
                        "bbox": [0, 10, 10, 20],
                        "table": {
                            "evidence_id": "ev_table",
                            "status": "parsed",
                            "reason": None,
                            "column_count": 2,
                            "row_count": 2,
                            "rows": [
                                [cell("ev_h1", "Ngành", header=True), cell("ev_h2", "Chỉ tiêu", header=True)],
                                [cell("ev_c1", "Công nghệ"), cell("ev_c2", "150")],
                            ],
                        },
                    },
                ],
            }
        ],
    }


def test_table_rows_are_atomic_and_headers_are_context_only():
    documents = [document()]
    units = split.build_units(documents)
    rows = [unit for unit in units if unit.kind == "table_row"]
    assert [unit.row_index for unit in rows] == [1]

    owned = split.owned_refs([rows[0]])
    assert owned == (
        {
            "kind": "table_rows",
            "ocr_run_id": "ocr_one",
            "page": 1,
            "evidence_id": "ev_table",
            "rows": [1],
            "header_rows": [0],
        },
    )
    context = split.context_refs(documents, [rows[0]])
    assert any(ref["kind"] == "table_header_rows" and ref["rows"] == [0] for ref in context)
    assert any(ref["evidence_id"] == "ev_title" for ref in context)

    payload, citations = split.build_projection(
        "Chủ đề", documents, owned, context, 1
    )
    table = payload["documents"][0]["pages"][0]["blocks"][-1]["table"]
    assert table["rows"] == [table["rows"][0], table["rows"][1]]
    assert table["rows"][0][0]["text"] == "Ngành"
    assert table["rows"][1][0]["text"] == "Công nghệ"
    assert "ev_c3" not in citations
    assert "ocr_one:ev_h1" in citations and "ocr_one:ev_c1" in citations
    assert payload["segment"]["owned"] == list(owned)
    assert payload["segment"]["context_only"] == list(context)


def test_output_budget_splits_even_when_all_input_fits():
    doc = document()
    doc["pages"][0]["blocks"] = [
        {"evidence_id": f"ev_{index}", "type": "text", "text": "Dữ kiện nguồn. " * 30}
        for index in range(12)
    ]
    original = copy.deepcopy(doc)
    unlimited = split.plan_segments([doc], "Nội dung", capacity=200_000, structured=True)
    assert len(unlimited) == 1
    tight = split.plan_segments(
        [doc], "Nội dung", capacity=200_000, structured=True, output_tokens=8192
    )
    generous = split.plan_segments(
        [doc], "Nội dung", capacity=200_000, structured=True, output_tokens=16384
    )
    assert len(tight) > 1 and len(generous) <= len(tight)
    for plans, budget in ((tight, 8192), (generous, 16384)):
        finalized = split.finalize_plans(
            plans, [doc], "Nội dung", capacity=200_000, structured=True
        )
        assert all(
            plan.output_size_estimate <= budget * split.OUTPUT_CONTENT_RATIO
            for plan in finalized
        )
        assert sum(len(plan.units) for plan in finalized) == 12
    assert doc == original


def test_output_budget_never_crops_one_oversized_row():
    doc = document()
    doc["pages"][0]["blocks"][1]["table"]["rows"][1][0]["text"] = "x" * 5000
    with pytest.raises(AppException) as error:
        split.plan_segments(
            [doc], "Nội dung", capacity=200_000, structured=False, output_tokens=8192
        )
    assert error.value.code == "compilation_segment_output_too_large"


def test_planner_packs_blocks_within_capacity_without_duplicate_ownership():
    documents = [document()]
    # Prose has no table-wide mandatory context; table conditions are tested above.
    documents[0]["pages"][0]["blocks"] = documents[0]["pages"][0]["blocks"][:1]
    blocks = documents[0]["pages"][0]["blocks"]
    for index in range(10):
        blocks.append(
            {
                "evidence_id": f"ev_b{index}",
                "type": "text",
                "text": ("Dữ kiện " + str(index) + " ") * 100,
                "bbox": [0, 0, 10, 10],
            }
        )
    original = copy.deepcopy(documents)
    plans = split.plan_segments(
        documents, "Chủ đề", capacity=6000, structured=False
    )
    plans = split.finalize_plans(
        plans, documents, "Chủ đề", capacity=6000, structured=False
    )
    assert len(plans) > 1
    assert all(plan.input_tokens <= 6000 for plan in plans)
    owned = [
        (ref["ocr_run_id"], ref["evidence_id"], tuple(ref.get("rows", ())))
        for plan in plans
        for ref in plan.owned
    ]
    block_refs = [ref for ref in owned if ref[2] == ()]
    assert len(block_refs) == len(set(block_refs))
    assert documents == original


def test_one_oversized_row_fails_instead_of_being_cropped():
    documents = [document()]
    table = documents[0]["pages"][0]["blocks"][1]
    table["text"] = ""
    table["table"]["rows"][1][1]["text"] = "x" * 4000
    with pytest.raises(AppException) as error:
        split.plan_segments(documents, "Chủ đề", capacity=900, structured=False)
    assert error.value.code == "compilation_segment_too_large"


def test_merge_is_backend_only_and_keeps_citations():
    part_one = {
        "title": "Ngưỡng 2026",
        "sections": [
            {
                "heading": "Chỉ tiêu",
                "paragraphs": [{"text": "Có 150 chỉ tiêu.", "citations": ["ocr_one:ev_c2"]}],
            }
        ],
        "unknowns": ["Chưa rõ đợt xét tuyển."],
    }
    part_two = {
        "title": "Ngưỡng 2026",
        "sections": [
            {
                "heading": "Chỉ tiêu",
                "paragraphs": [{"text": "Có 150 chỉ tiêu.", "citations": ["ocr_one:ev_c2"]}],
            },
            {
                "heading": "Ghi chú",
                "paragraphs": [{"text": "Nguồn năm 2026.", "citations": ["ocr_one:ev_c1"]}],
            },
        ],
        "unknowns": ["Chưa rõ đợt xét tuyển.", "Chưa rõ học phí."],
    }
    documents = [document()]
    merged = split.merge_drafts(
        [part_one, part_two],
        "Ngưỡng 2026",
        documents,
        "cmp_one",
        partial=False,
        segmentation={"state": "completed", "segments_total": 2, "segments_completed": 2},
    )
    assert [section["heading"] for section in merged["sections"]] == [
        "Chỉ tiêu",
        "Ghi chú",
    ]
    assert len(merged["sections"][0]["paragraphs"]) == 1
    assert merged["unknowns"] == ["Chưa rõ đợt xét tuyển.", "Chưa rõ học phí."]
    assert merged["citations"]["ocr_one:ev_c2"]["evidence_id"] == "ev_c2"
    assert merged["validation"]["semantic_faithfulness"] == "not_evaluated"


def test_partial_output_is_valid_with_empty_sections_and_never_published():
    merged = split.merge_drafts(
        [{"title": None, "sections": [], "unknowns": ["Chưa có phần nào."]}],
        "Ngưỡng 2026",
        [document()],
        "cmp_one",
        partial=True,
        segmentation={"state": "partial", "segments_total": 2, "segments_completed": 0},
    )
    assert merged["partial"] is True
    assert merged["sections"] == []
    assert merged["title"] == "Ngưỡng 2026"
    markdown = split.partial_markdown(merged).decode("utf-8")
    assert "Bản nháp một phần: 0/2 phần đã hoàn tất" in markdown
    with pytest.raises(AppException) as error:
        split.merge_drafts(
            [{"title": None, "sections": [], "unknowns": []}],
            "Ngưỡng 2026",
            [document()],
            "cmp_one",
            partial=False,
            segmentation={"state": "completed", "segments_total": 1, "segments_completed": 1},
        )
    assert error.value.code == "compilation_draft_empty"
