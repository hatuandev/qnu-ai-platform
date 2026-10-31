"""Review parts own each unit once, keep rows whole and expose only bounded context."""

import json

import pytest

from qnu.domains.knowledge.compilation.review import parts, report
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
    assert "phần 2/3" in messages[0].content


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
