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
    plans = parts.plan_parts(payload, capacity=8000, structured=False)
    assert len(plans) == 2
    assert all(plan.input_tokens <= 8000 for plan in plans)
    assert plans[1].source_ids == ("ocr_one:ev2",)
    assert "ocr_one:ev1" in plans[1].context_source_ids

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
        capacity=8000,
        output_tokens=1000,
    )
    assert len(manifest["segments"]) == 2
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
    plans = parts.plan_parts(payload, capacity=8000, structured=False)
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
    assert parts._source_context(payload, set(), set(reversed(selected)), order) == selected
