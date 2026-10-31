"""Projection v4: compact structural context, stable v2 bytes, honest budget.

The v2 hashes are pinned because a run planned with ``qnu.compiler.plan/v2`` stored
``input_sha256`` over exactly those bytes; editing the frozen module would make that
run impossible to resume or verify.
"""

import hashlib
import json

import pytest

from qnu.domains.knowledge.compilation import segments as split
from qnu.domains.knowledge.compilation import segments_v2
from qnu.platform.errors import AppException

# Derived by running the committed v2 module (commit 3b4224de) on ``v2_fixture``
# and hashing ``json.dumps(payload, ensure_ascii=False, sort_keys=True)``. It is a
# regression alarm for accidental edits, not a value to "fix" by copying whatever
# the current code prints: if it fails, diff ``projection.py``/``units.py`` first.
V2_PAYLOAD_SHA256 = "293877372456fd756217424a2c7244680894d647cf814e9cfc5e77cbd1e28c8f"
V2_PROMPT_SHA256 = "e561876e2fe490683dc50d1849f556856d7850c7314535967cc0f9f1e10aee06"


def cell(evidence_id: str, text: str, *, header: bool = False) -> dict:
    return {
        "evidence_id": evidence_id,
        "text": text,
        "header": header,
        "row_span": 1,
        "col_span": 1,
    }


def table_block(evidence_id: str, rows: list[list[dict]], columns: int = 2) -> dict:
    return {
        "evidence_id": evidence_id,
        "type": "table",
        "text": "",
        "bbox": [0, 0, 10, 10],
        "table": {
            "evidence_id": evidence_id,
            "status": "parsed",
            "reason": None,
            "column_count": columns,
            "row_count": len(rows),
            "rows": rows,
        },
    }


def text_block(evidence_id: str, text: str, kind: str = "text") -> dict:
    return {
        "evidence_id": evidence_id,
        "type": kind,
        "text": text,
        "bbox": [0, 0, 10, 10],
    }


def document(pages: list[list[dict]], run_id: str = "ocr_one") -> dict:
    return {
        "ocr_run_id": run_id,
        "canonical_sha256": "1" * 64,
        "manifest_sha256": "2" * 64,
        "identity": {"revision_id": "rev_one"},
        "evidence": {},
        "pages": [
            {"page_number": index + 1, "status": "ready", "blocks": blocks}
            for index, blocks in enumerate(pages)
        ],
    }


def two_page_table_document() -> dict:
    header = [cell("ev_h1", "Ngành", header=True), cell("ev_h2", "Chỉ tiêu", header=True)]
    first = [header, [cell("ev_c1", "Công nghệ"), cell("ev_c2", "150")]]
    second = [header, [cell("ev_c3", "Kinh tế"), cell("ev_c4", "140")]]
    return document(
        [
            [
                text_block("ev_title", "Bảng ngưỡng", "title"),
                table_block("ev_t1", first),
            ],
            [
                table_block("ev_t2", second),
                text_block("ev_note", "Điều kiện áp dụng cho các hàng trên.", "footnote"),
            ],
        ]
    )


def v2_fixture() -> dict:
    return document(
        [
            [
                text_block("ev_title", "Bảng ngưỡng", "title"),
                table_block(
                    "ev_table",
                    [
                        [cell("ev_h1", "Ngành", header=True), cell("ev_h2", "Chỉ tiêu", header=True)],
                        [cell("ev_c1", "Công nghệ"), cell("ev_c2", "150")],
                    ],
                ),
            ]
        ]
    )


def test_v2_request_bytes_are_pinned():
    documents = [v2_fixture()]
    units = split.build_units(documents)
    owned = split.owned_refs(units)
    context = segments_v2.context_refs(documents, units)
    payload, citations = segments_v2.build_projection(
        "Chủ đề", documents, owned, context, 1
    )
    user = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert hashlib.sha256(user.encode()).hexdigest() == V2_PAYLOAD_SHA256
    assert (
        hashlib.sha256(segments_v2.segment_system(1, 2).encode()).hexdigest()
        == V2_PROMPT_SHA256
    )
    delegated, delegated_citations = split.build_projection(
        "Chủ đề", documents, owned, context, 1, projection=split.PROJECTION_V2
    )
    assert delegated == payload and delegated_citations == citations


def test_v4_payload_has_no_repeated_document_text_and_marks_context_roles():
    documents = [two_page_table_document()]
    units = split.build_units(documents)
    rows = [unit for unit in units if unit.kind == "table_row"]
    payload, _ = split.build_projection(
        "Chủ đề", documents, split.owned_refs([rows[0]]), split.context_refs([documents[0]], [rows[0]]), 1, total=2
    )
    assert set(payload) == {
        "topic",
        "part",
        "outline",
        "table_links",
        "documents",
        "allowed_citations",
    }
    assert payload["part"]["total"] == 2
    roles = {ref["role"] for ref in payload["part"]["context_only"]}
    assert "table_header" in roles
    # The whole document outline is small; block text is not repeated per part.
    outline = json.dumps(payload["outline"], ensure_ascii=False)
    assert "Công nghệ" not in outline and "Kinh tế" not in outline
    assert "block_count" not in outline


def test_multi_page_tables_keep_headers_notes_without_asserting_continuation():
    documents = [two_page_table_document()]
    layout = split.build_layout(documents[0])
    assert layout.table_links == ()  # Same headers are not proof of continuation.
    legacy = split.build_layout(documents[0], legacy_v3=True)
    assert legacy.table_links[0]["to"] == "ev_t2"
    units = split.build_units(documents)
    for unit in [item for item in units if item.kind == "table_row"]:
        refs = split.context_refs(documents, [unit])
        assert any(ref["kind"] == "table_header_rows" for ref in refs)
        assert any(ref["evidence_id"] == "ev_note" for ref in refs)
    payload, _ = split.build_projection(
        "Chủ đề", documents, split.owned_refs(units), split.context_refs(documents, units), 1, total=1
    )
    assert payload["table_links"] == []
    # The trailing note is not dropped even though it is far from the first table.
    assert any(
        block["evidence_id"] == "ev_note"
        for page in payload["documents"][0]["pages"]
        for block in page["blocks"]
    )


def test_multi_level_headers_stay_context_for_every_data_row():
    """Two header rows are context; only data rows are owned, and row numbers survive."""
    header_one = [
        cell("ev_h1", "Ngành", header=True),
        cell("ev_h2", "Phương thức", header=True),
        cell("ev_h3", "Chỉ tiêu", header=True),
    ]
    header_two = [
        cell("ev_h4", "Mã", header=True),
        cell("ev_h5", "THPT", header=True),
        cell("ev_h6", "Điểm", header=True),
    ]
    rows = [
        header_one,
        header_two,
        [cell("ev_c1", "7480201"), cell("ev_c2", "x"), cell("ev_c3", "150")],
        [cell("ev_c4", "7340101"), cell("ev_c5", "y"), cell("ev_c6", "140")],
    ]
    documents = [
        document(
            [[text_block("ev_title", "Bảng ngưỡng", "title"), table_block("ev_t1", rows, columns=3)]]
        )
    ]
    units = split.build_units(documents)
    data = [unit for unit in units if unit.kind == "table_row"]
    assert [unit.row_index for unit in data] == [2, 3]
    assert all(unit.header_rows == (0, 1) for unit in data)
    owned = split.owned_refs(data)
    assert owned[0]["rows"] == [2, 3]
    assert owned[0]["header_rows"] == [0, 1]
    header_ref = next(
        ref for ref in split.context_refs(documents, data) if ref["kind"] == "table_header_rows"
    )
    assert header_ref["rows"] == [0, 1]
    payload, citations = split.build_projection(
        "Chủ đề", documents, owned, split.context_refs(documents, data), 1, total=1
    )
    table = payload["documents"][0]["pages"][0]["blocks"][1]["table"]
    # Header rows plus both data rows, in source order, never re-typed by the model.
    assert table["rows"] == rows
    assert table["row_numbers"] == [1, 2, 3, 4]
    assert "ocr_one:ev_h6" in citations


def test_context_does_not_repeat_unrelated_prose():
    documents = [
        document(
            [
                [
                    text_block("ev_title", "Mục", "title"),
                    text_block("ev_p1", "Đoạn văn dài không liên quan. " * 20),
                    text_block("ev_p2", "Đoạn văn khác. " * 20),
                    table_block("ev_t1", [[cell("ev_h1", "A", header=True)], [cell("ev_c1", "1")]]),
                ]
            ]
        )
    ]
    units = split.build_units(documents)
    row = next(unit for unit in units if unit.kind == "table_row")
    refs = split.context_refs(documents, [row])
    assert not any(ref["evidence_id"] in {"ev_p1", "ev_p2"} for ref in refs)


def test_long_tail_is_retained_as_unresolved_context():
    blocks = [table_block("ev_t1", [[cell("ev_h1", "A", header=True)], [cell("ev_c1", "1")]])]
    blocks.extend(text_block(f"ev_p{index}", "Đoạn văn. " * 30) for index in range(8))
    documents = [document([blocks])]
    layout = split.build_layout(documents[0])
    assert layout.note_tail_blocks == 8
    assert len(layout.trailing_notes) == 8
    assert all(ref["scope"] == "unresolved" for ref in layout.trailing_notes)
    outline = split.document_outline(documents, [layout])
    assert outline["documents"][0]["note_tail"]["shared_as_context"] is True
    units = split.build_units(documents)
    row = next(unit for unit in units if unit.kind == "table_row")
    assert {ref["evidence_id"] for ref in split.context_refs(documents, [row])} >= {f"ev_p{i}" for i in range(8)}
    assert split.build_layout(documents[0], legacy_v3=True).trailing_notes == ()


def test_one_long_note_is_not_dropped_by_the_old_byte_limit():
    blocks = [
        table_block("ev_t1", [[cell("ev_h1", "A", header=True)], [cell("ev_c1", "1")]]),
        text_block("ev_note", "Điều kiện cần đối chiếu. " * 300, "footnote"),
    ]
    documents = [document([blocks])]
    layout = split.build_layout(documents[0])
    assert layout.note_tail_bytes > 4000 and len(layout.trailing_notes) == 1
    row = next(unit for unit in split.build_units(documents) if unit.kind == "table_row")
    payload, _ = split.build_projection(
        "Chủ đề", documents, split.owned_refs([row]), split.context_refs(documents, [row]), 1,
    )
    projected = [block for page in payload["documents"][0]["pages"] for block in page["blocks"]]
    assert next(block for block in projected if block["evidence_id"] == "ev_note")["text"] == blocks[1]["text"]


def test_intermediate_table_retains_plain_text_notes_before_the_next_table():
    blocks = [
        table_block("ev_t1", [[cell("ev_h1", "A", header=True)], [cell("ev_c1", "1")]]),
        text_block("ev_note", "Điều kiện của bảng vừa nêu."),
        table_block("ev_t2", [[cell("ev_h2", "B", header=True)], [cell("ev_c2", "2")]]),
    ]
    documents = [document([blocks])]
    row = next(unit for unit in split.build_units(documents) if unit.kind == "table_row")
    refs = split.context_refs(documents, [row])
    note = next(ref for ref in refs if ref["evidence_id"] == "ev_note")
    assert note["scope"] == "unresolved"
    assert note["role"] == "neighbour_note"
    assert not any(ref["evidence_id"] == "ev_t2" for ref in refs)


@pytest.mark.parametrize("headers", [True, False])
def test_equal_headers_or_column_counts_cannot_link_distinct_tables(headers):
    rows = [[cell("ev_h", "A", header=True)]] if headers else []
    rows.append([cell("ev_c", "1")])
    source = document([[table_block("ev_first", rows)], [table_block("ev_second", rows)]])
    assert split.build_layout(source).table_links == ()
    assert split.build_layout(source, legacy_v3=True).table_links


def test_v3_replay_retains_the_previous_layout_and_prompt_contract():
    documents = [two_page_table_document()]
    legacy = split.build_layout(documents[0], legacy_v3=True)
    units = split.build_units(documents)
    # Stored scope refs are inputs to replay; v4 never regenerates them.
    owned = split.owned_refs([unit for unit in units if unit.kind == "table_row"])
    payload, _ = split.build_projection(
        "Chủ đề", documents, owned, legacy.trailing_notes, 1, projection=split.PROJECTION_V3,
    )
    assert payload["outline"] == split.document_outline(documents, [legacy])
    assert payload["table_links"] == list(legacy.table_links)
    assert payload["part"]["context_only"] == list(legacy.trailing_notes)
    assert "scope=unresolved" not in split.segment_system(1, 1, projection=split.PROJECTION_V3)
    assert split.prompt_version_for(split.PROJECTION_V3) == "qnu.compiler.segment.prompt/v3"


def test_plan_segments_covers_every_source_once_and_keeps_projection_version():
    documents = [
        two_page_table_document(),
        document([[text_block("ev_x", "Khối phụ.")]], run_id="ocr_two"),
    ]
    plans = split.plan_segments(
        documents, "Chủ đề", capacity=120_000, structured=True, output_tokens=8192
    )
    finalized = split.finalize_plans(
        plans, documents, "Chủ đề", capacity=120_000, structured=True
    )
    assert all(plan.projection == split.PROJECTION_V4 for plan in finalized)
    assert all("projection_version" in plan.scope_dict() for plan in finalized)
    restored = split.plan_from_scope(finalized[0].scope_dict())
    assert restored.projection == split.PROJECTION_V4
    assert restored.input_sha256 == finalized[0].input_sha256
    owned = [
        (ref["ocr_run_id"], ref["evidence_id"], tuple(ref.get("rows", ())))
        for plan in finalized
        for ref in plan.owned
    ]
    assert len(owned) == len(set(owned))


def test_legacy_scope_without_version_is_read_as_v2():
    plan = split.plan_from_scope(
        {
            "index": 1,
            "owned": [],
            "context": [],
            "input_sha256": "a" * 64,
            "schema_sha256": None,
        }
    )
    assert plan.projection == split.PROJECTION_V2
    assert split.prompt_version_for(plan.projection) == segments_v2.PROMPT_VERSION


def test_moderate_table_document_is_not_split_into_tiny_parts():
    """105 rows over 8 pages used to become ~15 parts under the 25% byte proxy."""
    pages = []
    number = 0
    for _ in range(8):
        blocks = []
        for _ in range(2):
            number += 1
            rows = [[cell(f"ev_{number}_h{column}", f"Cột {column}", header=True) for column in range(4)]]
            rows.extend(
                [
                    cell(f"ev_{number}_{row}_{column}", f"Ngành {row} phương thức {column} 15.0")
                    for column in range(4)
                ]
                for row in range(6)
            )
            blocks.append(table_block(f"ev_t{number}", rows, columns=4))
        pages.append(blocks)
    pages[-1].append(text_block("ev_note", "Ghi chú áp dụng cho toàn bảng.", "footnote"))
    documents = [document(pages)]
    plans = split.plan_segments(
        documents, "Chủ đề", capacity=122_880, structured=True, output_tokens=8192
    )
    finalized = split.finalize_plans(
        plans, documents, "Chủ đề", capacity=122_880, structured=True
    )
    assert 1 <= len(finalized) <= 4
    budget = split.output_content_bytes(8192)
    assert all(plan.output_size_estimate <= budget for plan in finalized)
    assert all(plan.input_tokens <= 122_880 for plan in finalized)


def test_unknown_projection_is_refused():
    documents = [two_page_table_document()]
    with pytest.raises(AppException) as error:
        split.build_projection("Chủ đề", documents, [], [], 1, projection="qnu.compiler.projection/v9")
    assert error.value.code == "compilation_segment_version_unsupported"
    with pytest.raises(AppException):
        split.prompt_version_for("qnu.compiler.projection/v9")
