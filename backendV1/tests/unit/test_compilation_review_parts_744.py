"""Review parts own each unit once, keep rows whole and expose only bounded context."""

import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.compilation.review import execution, literal, parts, report, text_spans
from qnu.domains.knowledge.compilation.review.material import (
    ReviewMaterial,
    draft_units,
    source_units,
)
from qnu.domains.knowledge.compilation.source_first import build_source_draft
from qnu.platform.errors import AppException


def source(unit_id: str, text: str, **extra) -> dict:
    return {
        "id": unit_id,
        "kind": "text",
        "text": text,
        "ocr_run_id": "ocr_one",
        "page": 1,
        "identity": {"revision_id": "rev_one"},
        "bbox": [0, 0, 10, 10],
        **extra,
    }


def paragraph(unit_id: str, text: str, citations: list[str]) -> dict:
    return {
        "id": unit_id,
        "kind": "paragraph",
        "text": text,
        "citations": citations,
    }


def material() -> dict:
    return {
        "topic": "Ngưỡng 2026",
        "documents": [{"ocr_run_id": "ocr_one", "identity": {"revision_id": "rev_one"}}],
        "source_units": [
            source("ocr_one:ev1", "Nguồn thứ nhất."),
            source("ocr_one:ev2", "Nguồn thứ hai."),
        ],
        "draft_units": [
            {"id": "title", "kind": "title", "text": "Ngưỡng 2026"},
            {"id": "section:1:heading", "kind": "heading", "text": "Chỉ tiêu"},
            paragraph("section:1:paragraph:1", "a" * 2500, ["ocr_one:ev1"]),
            {"id": "section:2:heading", "kind": "heading", "text": "Ghi chú"},
            paragraph("section:2:paragraph:1", "b" * 2500, ["ocr_one:ev2"]),
        ],
    }


@pytest.mark.parametrize("change", ["omit", "year", "number", "citation", "order", "duplicate"])
def test_retained_sections_reject_content_or_structure_drift(change):
    blocks = [
        {"evidence_id": "ev1", "type": "text", "bbox": None, "text": "Năm 2026 có 25 chỉ tiêu."},
        {"evidence_id": "ev2", "type": "text", "bbox": None, "text": "Năm 2025 có 19 chỉ tiêu."},
    ]
    docs = [
        {
            "ocr_run_id": "ocr_one",
            "identity": {},
            "canonical_sha256": "a" * 64,
            "manifest_sha256": "b" * 64,
            "pages": [{"page_number": 1, "blocks": blocks}],
            "evidence": {"ev1": {"page": 1}, "ev2": {"page": 1}},
        }
    ]
    topic = "Chỉ tiêu"
    draft = build_source_draft(topic, docs, "cmp_one")
    payload = {
        "topic": topic,
        "documents": docs,
        "draft": draft,
        "source_units": source_units(docs),
        "draft_units": draft_units(draft),
    }
    assert literal.retained_sections(payload, "cmp_one")
    assert len(literal.source_prose_pairs(payload)) == 2
    paras = draft["sections"][0]["paragraphs"]
    if change == "omit":
        paras.pop()
    elif change == "citation":
        paras[0]["citations"] = ["ocr_one:ev2"]
    elif change == "order":
        paras.reverse()
    elif change == "duplicate":
        paras.append(paras[0].copy())
    else:
        original, wrong = ("2026", "2024") if change == "year" else ("25", "52")
        paras[0]["text"] = paras[0]["text"].replace(original, wrong)
    assert not literal.retained_sections(payload, "cmp_one")


def test_flagged_and_shared_source_prose_is_not_assessed_locally():
    payload = material()
    payload["source_units"][0]["requires_review"] = True
    payload["draft_units"] = [
        paragraph("a", "Nguồn thứ nhất.", ["ocr_one:ev1"]),
        paragraph("b", "Nguồn thứ hai.", ["ocr_one:ev2"]),
        paragraph("c", "Phần nối.", ["ocr_one:ev1", "ocr_one:ev2"]),
    ]
    assert literal.source_prose_pairs(payload) == {}
    payload["draft_units"].pop()
    assert literal.source_prose_pairs(payload) == {"b": "ocr_one:ev2"}


def test_title_review_includes_its_exact_source_even_if_not_a_prose_pair():
    payload = material()
    payload["source_units"].append(source("ocr_one:title", "NGƯỠNG 2026", page=1, kind="title"))
    payload["draft_units"] = [
        payload["draft_units"][0],
        paragraph("copied", "Nguồn thứ nhất.", ["ocr_one:ev1"]),
    ]
    plans = parts.plan_parts(
        payload, capacity=24000, structured=True, source_copies={"copied": "ocr_one:ev1"}
    )
    title = next(plan for plan in plans if "title" in plan.draft_ids)
    assert title.context_source_ids == ("ocr_one:title",)
    assert any("ocr_one:title" in plan.source_ids for plan in plans)


def test_plan_covers_every_unit_once_and_repeats_earlier_source_as_context():
    payload = material()
    # The review instructions now cost ~4.8K byte-bound tokens; allow room for
    # one claim plus its evidence/context, still too small for the whole fixture.
    plans = parts.plan_parts(payload, capacity=11000, structured=False)
    assert len(plans) > 1
    assert all(plan.input_tokens <= 11000 for plan in plans)
    second_source = next(plan for plan in plans if "ocr_one:ev2" in plan.source_ids)
    assert "ocr_one:ev1" in second_source.context_source_ids

    owned_sources = [key for plan in plans for key in plan.source_ids]
    owned_drafts = [key for plan in plans for key in plan.draft_ids]
    assert set(owned_sources) == {"ocr_one:ev1", "ocr_one:ev2"}
    assert len(owned_sources) == len(set(owned_sources))
    assert set(owned_drafts) == {
        "title",
        "section:1:heading",
        "section:1:paragraph:1",
        "section:2:heading",
        "section:2:paragraph:1",
    }

    manifest = parts.manifest_for(
        type(
            "Review",
            (),
            {
                "id": "rvw_one",
                "compilation_run_id": "cmp_one",
                "bundle_sha256": "a" * 64,
            },
        )(),
        plans,
        payload,
        capacity=11000,
        output_tokens=1000,
    )
    assert len(manifest["segments"]) == len(plans)
    assert manifest["coverage"]["source_unit_count"] == 2
    assert manifest["coverage"]["draft_unit_count"] == 5


def test_source_only_parts_never_split_a_table_row():
    units = []
    for column in (1, 2):
        units.append(
            source(
                f"ocr_one:h{column}",
                "Tiêu đề",
                kind="table_cell",
                table_id="ocr_one:t1",
                row=1,
                column=column,
                header=True,
                source_id=None,
            )
        )
    for row in (2, 3, 4):
        for column in (1, 2):
            units.append(
                source(
                    f"ocr_one:c{row}{column}",
                    "x" * 1200,
                    kind="table_cell",
                    table_id="ocr_one:t1",
                    row=row,
                    column=column,
                    header=False,
                    source_id=None,
                )
            )
    payload = {
        "topic": "Bảng",
        "documents": [{"ocr_run_id": "ocr_one", "identity": {"revision_id": "rev_one"}}],
        "source_units": units,
        "draft_units": [],
    }
    plans = parts.plan_parts(payload, capacity=14000, structured=False)
    assert len(plans) > 1
    all_ids = {unit["id"] for unit in units}
    owned = [key for plan in plans for key in plan.source_ids]
    assert set(owned) == all_ids and len(owned) == len(set(owned))
    by_id = {unit["id"]: unit for unit in units}
    for plan in plans:
        rows = {}
        for key in plan.source_ids:
            unit = by_id[key]
            rows.setdefault((unit["table_id"], unit["row"]), []).append(unit["column"])
        assert all(sorted(columns) == [1, 2] for columns in rows.values())


def test_validate_content_allows_only_context_references_and_requires_exact_coverage():
    payload = material()
    part = parts.payload_for(
        payload,
        ["ocr_one:ev2"],
        ["section:2:paragraph:1"],
        ["ocr_one:ev1"],
        ["section:1:paragraph:1"],
    )
    content = json.dumps(
        {
            "source_assessments": [
                {
                    "source_id": "ocr_one:ev2",
                    "status": "covered",
                    "draft_ids": ["section:1:paragraph:1"],
                    "explanation": "Đã đối chiếu phần liên quan.",
                    "suggested_action": "",
                }
            ],
            "draft_assessments": [
                {
                    "draft_id": "section:2:paragraph:1",
                    "status": "supported",
                    "source_ids": ["ocr_one:ev1"],
                    "explanation": "Nguồn ngữ cảnh xác nhận phạm vi.",
                    "suggested_action": "",
                }
            ],
        },
        ensure_ascii=False,
    )
    value = report.validate_content(content, part)
    assert value.source_assessments[0].draft_ids == ["section:1:paragraph:1"]

    missing = json.loads(content)
    missing["draft_assessments"] = []
    with pytest.raises(AppException) as error:
        report.validate_content(json.dumps(missing), part)
    assert error.value.code == "compilation_review_invalid"


def test_reusable_keyed_does_not_accept_foreign_or_duplicate_ids():
    part = parts.payload_for(
        material(), ["ocr_one:ev2"], ["section:2:paragraph:1"], ["ocr_one:ev1"], []
    )
    check = {
        "status": "covered",
        "draft_ids": ["section:2:paragraph:1"],
        "explanation": "Khớp.",
        "suggested_action": "",
    }
    keyed = {
        "source_assessments": {"ocr_one:ev2": check, "ocr_one:ev1": check},
        "draft_assessments": {},
    }
    content = json.dumps(keyed)
    result = report.reusable_keyed(content, part)
    assert result is not None
    accepted, ignored = result
    assert [item.source_id for item in accepted.source_assessments] == ["ocr_one:ev2"]
    assert ignored == 1
    assert report.reusable_keyed(content.replace('"ocr_one:ev1"', '"ocr_one:ev2"'), part) is None
    assert report.reusable_keyed(content.replace('"ocr_one:ev1"', '"other:ev1"'), part) is None


def test_provider_report_keeps_limited_unverified_units_as_findings():
    source = material()
    part = parts.payload_for(
        source,
        ["ocr_one:ev1", "ocr_one:ev2"],
        ["section:1:paragraph:1", "section:2:paragraph:1"],
    )
    payload = {
        "source_assessments": [
            {"source_id": "ocr_one:ev1", "status": "covered", "draft_ids": []},
            {
                "source_id": "ocr_one:ev2",
                "status": "covered",
                "draft_ids": ["section:2:paragraph:1"],
            },
        ],
        "draft_assessments": [
            {
                "draft_id": "section:2:paragraph:1",
                "status": "supported",
                "source_ids": ["ocr_one:unknown", "ocr_one:ev2"],
            }
        ],
    }
    for entries in payload.values():
        for entry in entries:
            entry.update(explanation="Nhận xét của mô hình", suggested_action="")

    assessed = report.validate_content(json.dumps(payload), part, unverified="exhausted")
    checked = report.validate_content(assessed.model_dump_json(), part)
    assert [unit.status for unit in checked.source_assessments] == ["uncertain", "covered"]
    assert all(
        unit.status == "uncertain" and not unit.source_ids for unit in checked.draft_assessments
    )
    built = report.report_from_assessments(checked, part, "rvw_test", "a" * 64)
    assert built["verdict"] == "needs_attention"
    assert built["summary"]["finding_count"] == 3

    for changes in ([], [dict(payload["draft_assessments"][0], draft_id="section:unknown")]):
        bad = {**payload, "draft_assessments": changes}
        with pytest.raises(AppException) as error:
            report.validate_content(json.dumps(bad), part, unverified="exhausted")
        assert error.value.code == "compilation_review_invalid"


def test_part_messages_carry_owned_units_and_small_context_not_full_snapshot():
    payload = material()
    part = parts.payload_for(
        payload,
        ["ocr_one:ev2"],
        ["section:2:paragraph:1"],
        ["ocr_one:ev1"],
        ["section:1:paragraph:1"],
    )
    messages = parts.messages_for(part, structured=False, index=2, total=3)
    user = json.loads(messages[-1].content)
    assert user["topic"] == "Ngưỡng 2026"
    assert [unit["id"] for unit in user["source_units"]] == ["ocr_one:ev2"]
    assert [unit["id"] for unit in user["draft_units"]] == ["section:2:paragraph:1"]
    assert [unit["id"] for unit in user["context_source_units"]] == ["ocr_one:ev1"]
    assert "pages" not in user["documents"][0]
    # Prompt v3 states ownership and does not depend on how many sibling parts exist.
    assert "đúng 1 đơn vị trong source_units" in messages[0].content
    assert "tuyệt đối không tạo nhận xét" in messages[0].content
    other_total = parts.messages_for(part, structured=False, index=2, total=9)
    assert other_total[0].content == messages[0].content
    # Prompt v2 stays reproducible for plans stored before v3.
    legacy = parts.messages_for(
        part,
        structured=False,
        index=2,
        total=3,
        prompt_version=parts.LEGACY_SEGMENT_PROMPT_VERSION,
    )
    assert "phần 2/3" in legacy[0].content


def test_required_citations_exceeding_neighbour_cap_are_not_dropped():
    payload = material()
    payload["source_units"] = [source(f"source_{i}", f"Nội dung {i}") for i in range(25)]
    order = {unit["id"]: i for i, unit in enumerate(payload["source_units"])}
    cited = set(order)
    selected = parts._source_context(payload, set(), cited, order)
    assert selected == list(order)
    assert parts._source_context(payload, set(), set(selected), order) == selected


def test_too_small_capacity_is_rejected_without_dropping_owned_units():
    with pytest.raises(AppException) as caught:
        parts.plan_parts(material(), capacity=8000, structured=True)
    assert caught.value.code == "compilation_review_segment_too_large"


def test_text_spans_reject_changed_draft_or_incomplete_saved_offsets():
    payload = material()
    paragraph_id = "section:1:paragraph:1"
    ref = "ocr_one:ev1"
    payload["source_units"] = [source(ref, "a" * 45000)]
    payload["draft_units"] = [paragraph(paragraph_id, "a" * 44999 + "b", [ref])]
    review = ReviewMaterial(None, payload)
    with pytest.raises(AppException) as error:
        text_spans.plan(
            review,
            capacity=32000,
            output_tokens=4096,
            reasoning_shares_budget=False,
            structural_drafts=(),
        )
    assert error.value.code == "compilation_review_segment_too_large"

    payload["draft_units"][0]["text"] = "a" * 45000
    with pytest.raises(AppException) as error:
        text_spans.apply_layout(review, {ref: {paragraph_id: [20000, 40000]}})
    assert error.value.code == "compilation_review_text_span_mismatch"


def test_cited_table_row_and_headers_are_mandatory_beyond_neighbour_cap():
    payload = material()
    payload["source_units"] = [
        source(
            f"cell_{i}",
            str(i),
            kind="table_cell",
            table_id="ocr_one:table",
            row=1 if i < 20 else 2,
            header=i < 20,
        )
        for i in range(40)
    ]
    order = {unit["id"]: i for i, unit in enumerate(payload["source_units"])}
    context = parts._source_context(payload, set(), {"cell_39"}, order)
    assert set(context) == set(order)


def test_table_block_citation_resolves_to_cells_as_read_only_context():
    payload = material()
    payload["source_units"] = [
        source(
            f"cell_{i}",
            str(i),
            kind="table_cell",
            table_id="ocr_one:table",
            row=1,
        )
        for i in range(3)
    ]
    payload["draft_units"] = [paragraph("p", "Nhận xét bảng.", ["ocr_one:table"])]
    plans, owned = parts._build_group(
        payload, ["p"], set(), index=1, total=2, structured=True, capacity=100000
    )
    assert not owned
    assert set(plans[0].context_source_ids) == {"cell_0", "cell_1", "cell_2"}


def test_review_projection_preserves_legacy_replay_and_full_snapshot():
    payload = material()
    legacy = parts.build_part(
        payload,
        index=1,
        total=1,
        source_ids=["ocr_one:ev1"],
        draft_ids=[],
        structured=True,
        projection="full",
    )
    assert "projection" not in legacy.scope_dict()
    rebuilt, _, _ = parts.rebuild_part(payload, legacy.scope_dict(), total=1, structured=True)
    assert rebuilt.input_sha256 == legacy.input_sha256
    compact = parts.build_part(
        payload, index=1, total=1, source_ids=["ocr_one:ev1"], draft_ids=[], structured=True
    )
    assert "identity" not in compact.payload["source_units"][0]
    assert "identity" in payload["source_units"][0]
    assert compact.payload["source_units"][0]["text"] == payload["source_units"][0]["text"]


def test_input_fits_131k_context_but_large_estimated_output_triggers_4096_split():
    """Batch 1 (1, 2, 4): Input fits 131072 context, but 4096 output budget forces splitting."""
    sources = [source(f"ocr_one:ev_{i}", f"Dữ kiện tuyển sinh {i}.") for i in range(45)]
    drafts = [
        {"id": "title", "kind": "title", "text": "Tổng hợp ngưỡng 2026"},
        {"id": "section:1:heading", "kind": "heading", "text": "Chi tiết ngành"},
        *[
            paragraph(
                f"section:1:paragraph:{i + 1}",
                f"Nội dung đoạn {i + 1} đối chiếu nguồn.",
                [f"ocr_one:ev_{i}"],
            )
            for i in range(45)
        ],
    ]
    payload = {
        "topic": "Ngưỡng 2026",
        "documents": [{"ocr_run_id": "ocr_one", "identity": {"revision_id": "rev_one"}}],
        "source_units": sources,
        "draft_units": drafts,
    }
    capacity = 131072 - 4096
    assert parts.requires_output_segmentation(
        payload,
        output_tokens=4096,
        structured=True,
        reasoning_shares_budget=True,
    )
    budget = parts.output_budget(4096, reasoning_shares_budget=True)
    assert budget.usable_output_tokens < 4096
    assert budget.reasoning_reserve_tokens > 0 and budget.framing_reserve_tokens > 0

    plans = parts.plan_parts(
        payload,
        capacity=capacity,
        output_tokens=4096,
        structured=True,
        reasoning_shares_budget=True,
    )
    assert len(plans) > 1
    for plan in plans:
        assert plan.input_tokens <= capacity
        assert plan.output_tokens_estimate <= budget.usable_output_tokens
        assert plan.max_output_tokens == 4096
        scope = plan.scope_dict()
        assert scope["budget"]["max_output_tokens"] == 4096
        assert scope["budget"]["output_budget_tokens"] == budget.usable_output_tokens
        assert scope["replay"]["planner_version"] == parts.PLANNER_VERSION
        assert scope["replay"]["prompt_sha256"]

    owned_sources = [key for plan in plans for key in plan.source_ids]
    owned_drafts = [key for plan in plans for key in plan.draft_ids]
    assert len(owned_sources) == len(sources) == len(set(owned_sources))
    assert len(owned_drafts) == len(drafts) == len(set(owned_drafts))


def test_long_tables_preserve_parent_headings_headers_notes_rowspans_and_table_boundaries():
    """Batch 1 (3, 4): Long tables split by row groups, keep headers/titles/notes, never merge tables."""
    source_units = [
        source("ocr_one:doc_title", "Đề án tuyển sinh 2026", kind="title"),
        source("ocr_one:t1_unit", "Đơn vị tính: chỉ tiêu", kind="caption"),
        source(
            "ocr_one:t1_h1",
            "Ngành",
            kind="table_cell",
            table_id="ocr_one:t1",
            row=1,
            column=1,
            header=True,
        ),
        source(
            "ocr_one:t1_h2",
            "Chỉ tiêu",
            kind="table_cell",
            table_id="ocr_one:t1",
            row=1,
            column=2,
            header=True,
        ),
    ]
    for row in range(2, 18):
        row_span = 2 if row == 2 else 1
        source_units.extend(
            [
                source(
                    f"ocr_one:t1_r{row}_c1",
                    f"Ngành {row}",
                    kind="table_cell",
                    table_id="ocr_one:t1",
                    row=row,
                    column=1,
                    row_span=row_span,
                    header=False,
                ),
                source(
                    f"ocr_one:t1_r{row}_c2",
                    str(100 + row),
                    kind="table_cell",
                    table_id="ocr_one:t1",
                    row=row,
                    column=2,
                    row_span=1,
                    header=False,
                ),
            ]
        )
    source_units.append(
        source("ocr_one:t1_note", "Ghi chú: áp dụng cho hệ chính quy.", kind="footnote")
    )
    # Second table with identical header text must never merge with t1.
    source_units.extend(
        [
            source(
                "ocr_one:t2_h1",
                "Ngành",
                kind="table_cell",
                table_id="ocr_one:t2",
                row=1,
                column=1,
                header=True,
            ),
            source(
                "ocr_one:t2_h2",
                "Chỉ tiêu",
                kind="table_cell",
                table_id="ocr_one:t2",
                row=1,
                column=2,
                header=True,
            ),
            source(
                "ocr_one:t2_r2_c1",
                "Sư phạm Toán",
                kind="table_cell",
                table_id="ocr_one:t2",
                row=2,
                column=1,
                header=False,
            ),
            source(
                "ocr_one:t2_r2_c2",
                "80",
                kind="table_cell",
                table_id="ocr_one:t2",
                row=2,
                column=2,
                header=False,
            ),
        ]
    )
    payload = {
        "topic": "Chỉ tiêu 2026",
        "documents": [{"ocr_run_id": "ocr_one", "identity": {"revision_id": "rev_one"}}],
        "source_units": source_units,
        "draft_units": [
            {"id": "title", "kind": "title", "text": "Chỉ tiêu 2026"},
            {"id": "section:1:heading", "kind": "heading", "text": "Bảng chỉ tiêu"},
            paragraph("section:1:paragraph:1", "Tổng hợp chỉ tiêu.", ["ocr_one:doc_title"]),
        ],
    }
    plans = parts.plan_parts(
        payload,
        capacity=120000,
        output_tokens=600,
        structured=True,
    )
    assert len(plans) >= 4
    # Row 2 and Row 3 of t1 are linked by row_span=2 and must stay in the same part.
    r2_part = next(p for p in plans if "ocr_one:t1_r2_c1" in p.source_ids)
    assert "ocr_one:t1_r3_c1" in r2_part.source_ids and "ocr_one:t1_r3_c2" in r2_part.source_ids
    # Every part owning data rows of t1 must carry t1 headers, title/unit and footnote in context or owned.
    for plan in plans:
        if any(uid.startswith("ocr_one:t1_r") for uid in plan.source_ids):
            visible = set(plan.source_ids) | set(plan.context_source_ids)
            assert {"ocr_one:t1_h1", "ocr_one:t1_h2"} <= visible
            assert "ocr_one:doc_title" in visible
            assert "ocr_one:t1_unit" in visible
            assert "ocr_one:t1_note" in visible
            # Must not merge t2 data rows into t1 row groups unless budget grouped separate whole groups.
            for uid in plan.source_ids:
                if uid.startswith("ocr_one:t1_r"):
                    row_no = uid.split("_r", 1)[1].split("_", 1)[0]
                    assert f"ocr_one:t1_r{row_no}_c1" in plan.source_ids
                    assert f"ocr_one:t1_r{row_no}_c2" in plan.source_ids


def test_indivisible_unit_exceeding_output_budget_raises_contract_error():
    """Batch 1 (5): A single atomic unit that cannot fit the output budget fails with 422 contract code."""
    payload = material()
    with pytest.raises(AppException) as caught:
        parts.plan_parts(
            payload,
            capacity=120000,
            output_tokens=80,
            structured=True,
        )
    assert caught.value.status_code == 422
    assert caught.value.code == "compilation_review_segment_too_large"


def test_review_collapses_repeated_links_only_after_validating_their_scope():
    payload = {"source_units": [{"id": "source"}], "draft_units": [{"id": "draft"}]}
    source_check = {
        "source_id": "source",
        "status": "covered",
        "draft_ids": ["draft", "draft"],
        "explanation": "Có nội dung tương ứng.",
        "suggested_action": "",
    }
    draft_check = {
        "draft_id": "draft",
        "status": "supported",
        "source_ids": ["source"] * 4,
        "explanation": "Khớp nội dung nguồn.",
        "suggested_action": "",
    }
    content = {"source_assessments": [source_check], "draft_assessments": [draft_check]}
    checked = report.validate_content(json.dumps(content), payload)
    assert checked.source_assessments[0].draft_ids == ["draft"]
    assert checked.draft_assessments[0].source_ids == ["source"]

    draft_check["source_ids"].append("outside")
    with pytest.raises(AppException) as invalid:
        report.validate_content(json.dumps(content), payload)
    assert invalid.value.code == "compilation_review_invalid"


def test_large_rowspan_keeps_anchor_citations_and_checks_exact_cells_locally():
    table_id = "ocr_one:table"
    units = [
        source(
            f"ocr_one:cell{row}",
            "Nội dung ô nguồn " * 180 if row > 2 else "Đầu bảng",
            kind="table_cell",
            table_id=table_id,
            row=row,
            column=1,
            row_span=11 if row == 2 else 1,
            col_span=1,
            header=row == 1,
        )
        for row in range(1, 13)
    ]
    copied = [
        {
            **unit,
            "id": f"table:1:row:{unit['row']}:cell:1",
            "source_id": unit["id"],
        }
        for unit in units
    ]
    claim = paragraph("claim", "Đoạn dẫn ô gộp.", [units[1]["id"]])
    payload = {
        "topic": "Bảng gộp hàng",
        "documents": [{"ocr_run_id": "ocr_one"}],
        "source_units": units,
        "draft_units": [claim, *copied],
        "draft": {"source_tables": [{"citation": table_id}]},
    }
    plans = parts.plan_parts(payload, capacity=16000, structured=True)
    claim_plan = next(plan for plan in plans if claim["id"] in plan.draft_ids)
    assert {unit["id"] for unit in units[:2]} <= set(claim_plan.context_source_ids)
    assert units[-1]["id"] not in claim_plan.context_source_ids
    assert claim_plan.source_ids == ()
    assert not claim_plan.literal_only

    local = next(plan for plan in plans if plan.literal_only)
    assert {unit["id"] for unit in units[1:]} <= set(local.source_ids)
    assert local.input_tokens > 16000
    rebuilt, _, _ = parts.rebuild_part(
        payload, local.scope_dict(), total=len(plans), structured=True
    )
    assert rebuilt.literal_only
    assert rebuilt.input_sha256 == local.input_sha256

    copied[-1]["text"] = "Ô bị sửa."
    with pytest.raises(AppException) as caught:
        parts.plan_parts(payload, capacity=16000, structured=True)
    assert caught.value.code == "compilation_review_segment_too_large"


def test_block_cited_table_larger_than_one_call_defers_the_draft_with_an_explicit_uncertain():
    """The cells keep their source parts; the draft records a server-built uncertain finding."""
    units = [
        source(
            f"ocr_one:t1_h{column}",
            "Tiêu đề " * 200,
            kind="table_cell",
            table_id="ocr_one:t1",
            row=1,
            column=column,
            header=True,
        )
        for column in (1, 2)
    ]
    for row in range(2, 82):
        for column in (1, 2):
            units.append(
                source(
                    f"ocr_one:t1_r{row}_c{column}",
                    "Nội dung ô. " * 100,
                    kind="table_cell",
                    table_id="ocr_one:t1",
                    row=row,
                    column=column,
                    header=False,
                )
            )
    units.append(source("ocr_one:ev1", "Nguồn văn bản riêng."))
    payload = {
        "topic": "Chỉ tiêu 2026",
        "documents": [{"ocr_run_id": "ocr_one", "identity": {"revision_id": "rev_one"}}],
        "source_units": units,
        "draft_units": [
            {"id": "title", "kind": "title", "text": "Chỉ tiêu 2026"},
            {"id": "section:1:heading", "kind": "heading", "text": "Bảng chỉ tiêu"},
            paragraph(
                "section:1:paragraph:1",
                "Tổng hợp toàn bộ chỉ tiêu trong bảng.",
                ["ocr_one:t1"],
            ),
            paragraph("section:2:paragraph:1", "Ghi chú tuyển sinh.", ["ocr_one:ev1"]),
        ],
    }
    plans = parts.plan_parts(payload, capacity=20000, structured=False)
    limited = [plan for plan in plans if plan.preassessed_drafts]
    assert len(limited) == 1
    part = limited[0]
    assert part.source_ids == ()
    assert part.draft_ids == ("section:1:paragraph:1",)
    assessment = part.preassessed_drafts[0]
    assert assessment["draft_id"] == "section:1:paragraph:1"
    assert assessment["status"] == "uncertain"
    assert assessment["source_ids"] == []
    assert "Ngữ cảnh bắt buộc vượt ngân sách" in assessment["explanation"]
    assert "162 ô" in assessment["explanation"]

    scope = json.loads(json.dumps(part.scope_dict()))
    assert scope["preassessed_drafts"][0]["draft_id"] == "section:1:paragraph:1"
    rebuilt, _, _ = parts.rebuild_part(payload, scope, total=len(plans), structured=False)
    assert rebuilt.input_sha256 == part.input_sha256
    assert rebuilt.preassessed_drafts == part.preassessed_drafts

    checked = report.validate_content(
        json.dumps(
            {"source_assessments": [], "draft_assessments": list(part.preassessed_drafts)},
            ensure_ascii=False,
        ),
        part.payload,
    )
    assert checked.draft_assessments[0].draft_id == "section:1:paragraph:1"

    owned_sources = [key for plan in plans for key in plan.source_ids]
    owned_drafts = [key for plan in plans for key in plan.draft_ids]
    assert set(owned_sources) == {unit["id"] for unit in units}
    assert len(owned_sources) == len(set(owned_sources))
    assert set(owned_drafts) == {unit["id"] for unit in payload["draft_units"]}
    assert len(owned_drafts) == len(set(owned_drafts))
    # Every cell of the block-cited table is still reviewed by a source-only part.
    assert sum(1 for key in owned_sources if key.startswith("ocr_one:t1_")) == len(units) - 1


@pytest.mark.parametrize("change", [None, "text", "cell", "warning", "citations"])
def test_table_text_copy_requires_literal_block_and_table_in_pinned_source(change):
    ref = "ocr_one:t1"
    table = {"status": "parsed", "rows": [[{"evidence_id": "c1", "text": "Năm 2026"}]]}
    block = {"evidence_id": "t1", "text": "Năm 2026 | 25", "table": table}
    entry = {"citation": ref, "table": deepcopy(table)}
    draft = paragraph("section:1:paragraph:1", block["text"], [ref])
    if change == "text":
        draft["text"] = "Năm 2026 | 26"
    elif change == "cell":
        entry["table"]["rows"][0][0]["text"] = "Năm 2025"
    elif change == "warning":
        block["requires_review"] = True
    elif change == "citations":
        draft["citations"].append("ocr_one:unrelated")
    payload = {
        "documents": [{"ocr_run_id": "ocr_one", "pages": [{"blocks": [block]}]}],
        "draft": {"source_tables": [entry]},
        "draft_units": [draft],
        "source_units": [source("ocr_one:c1", "Năm 2026", kind="table_cell", table_id=ref)],
    }
    checks = literal.assess_table_text_copies(payload)
    if change:
        assert checks == ()
    else:
        (check,) = checks
        assert check["draft_id"] == draft["id"]
        assert check["source_ids"] == ["ocr_one:c1"]
        assert check["status"] == "supported"


@pytest.mark.asyncio
async def test_manifest_rejects_modified_planner_assessment(monkeypatch):
    scope = {
        "index": 1,
        "source_ids": [],
        "draft_ids": ["draft"],
        "context_source_ids": [],
        "context_draft_ids": [],
        "input_sha256": "request",
        "preassessed_drafts": [{"draft_id": "draft", "status": "uncertain"}],
    }
    review = SimpleNamespace(
        id="review", bundle_sha256="bundle", trace={"segmentation": {"manifest_sha256": "plan"}}
    )
    manifest = json.dumps(
        {"review_id": review.id, "bundle_sha256": review.bundle_sha256, "segments": [scope]}
    ).encode()
    monkeypatch.setattr(
        execution.artifacts,
        "read",
        AsyncMock(return_value=(SimpleNamespace(sha256="plan"), manifest)),
    )
    part = SimpleNamespace(
        id="segment",
        parent_segment_id=None,
        segment_index=1,
        config={},
        input_sha256=scope["input_sha256"],
        scope=scope.copy(),
    )
    await execution._verify_manifest(None, None, review, [part])
    part.scope["preassessed_drafts"] = []
    with pytest.raises(AppException) as error:
        await execution._verify_manifest(None, None, review, [part])
    assert error.value.code == "compilation_review_segment_manifest_mismatch"


def test_planner_finding_links_to_pinned_table_without_claiming_support():
    paragraph_unit = paragraph("p", "Tóm tắt bảng.", ["ocr_one:table"])
    payload = {
        "topic": "Một bảng",
        "source_units": [],
        "draft_units": [paragraph_unit],
        "draft": {
            "citations": {
                "ocr_one:table": {"source_id": "source", "revision_id": "rev", "file_name": "a.pdf"}
            },
            "source_tables": [{"citation": "ocr_one:table", "page_number": 11}],
        },
    }
    value = report.validate_content(
        json.dumps(
            {
                "source_assessments": [],
                "draft_assessments": [
                    {
                        "draft_id": "p",
                        "status": "uncertain",
                        "source_ids": [],
                        "explanation": "Cần đối chiếu.",
                        "suggested_action": "",
                    }
                ],
            }
        ),
        payload,
    )
    result = report.report_from_assessments(
        value, payload, "review", "bundle", planner_limited={"p"}
    )
    (finding,) = result["findings"]
    assert result["verdict"] == "needs_attention"
    assert finding["sources"] == []
    assert finding["source_locations"] == [
        {
            "source_id": "source",
            "revision_id": "rev",
            "file_name": "a.pdf",
            "page": 11,
            "table_number": 1,
        }
    ]
    assert "Trang 11" in report.markdown_for(result).decode()
