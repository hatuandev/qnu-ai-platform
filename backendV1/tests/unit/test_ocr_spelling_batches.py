"""Adaptive spelling batches stay inside the declared input envelope."""

import json

from qnu.domains.modelops.capacity.schemas import ModelTokenLimits
from qnu.domains.ocr.review import automatic
from qnu.domains.ocr.review.schemas import ContextSuggestedText, TextUnit


def document(count: int, size: int = 40):
    rows = {
        f"ev_{index:03d}": TextUnit(
            evidence_id=f"ev_{index:03d}",
            page=1,
            kind="paragraph",
            text=("nội dung kiểm tra chính tả " * (size // 25 + 1))[:size],
            original_text="",
            bbox={},
        )
        for index in range(count)
    }
    canonical = {
        "pages": [
            {
                "page_number": 1,
                "blocks": [
                    {"evidence_id": key, "type": "paragraph", "text": unit.text}
                    for key, unit in rows.items()
                ],
            }
        ]
    }
    return rows, canonical


def schema_size() -> int:
    return len(
        json.dumps(ContextSuggestedText.model_json_schema(), ensure_ascii=False).encode()
    )


def test_batches_are_capped_and_cover_every_unit_in_order(monkeypatch):
    monkeypatch.setattr(automatic, "BATCH_SIZE", 4)
    rows, canonical = document(11)
    ids = list(rows)
    limits = ModelTokenLimits(context_window_tokens=131072, max_output_tokens=8192)

    batches = automatic.plan_batches(ids, rows, canonical, 0, "0" * 64, limits, 8192)

    assert [offset for offset, _ in batches] == [0, 4, 8]
    assert [len(group) for _, group in batches] == [4, 4, 3]
    assert [evidence_id for _, group in batches for evidence_id in group] == ids


def test_small_envelope_yields_smaller_batches(monkeypatch):
    monkeypatch.setattr(automatic, "BATCH_SIZE", 25)
    rows, canonical = document(8, size=300)
    ids = list(rows)
    single = automatic._upper_bound([ids[0]], rows, canonical, 0, "0" * 64, schema_size())
    wide = ModelTokenLimits(context_window_tokens=131072, max_output_tokens=8192)
    narrow = ModelTokenLimits(max_input_tokens=single + 120, max_output_tokens=1024)

    wide_batches = automatic.plan_batches(ids, rows, canonical, 0, "0" * 64, wide, 8192)
    narrow_batches = automatic.plan_batches(ids, rows, canonical, 0, "0" * 64, narrow, 1024)

    assert [len(group) for _, group in wide_batches] == [8]
    assert len(narrow_batches) > 1
    assert all(len(group) < 8 for _, group in narrow_batches)
    assert [evidence_id for _, group in narrow_batches for evidence_id in group] == ids
    available = automatic.available_input_tokens(narrow, 1024)
    assert all(
        len(group) == 1
        or automatic._upper_bound(group, rows, canonical, 0, "0" * 64, schema_size())
        <= available
        for _, group in narrow_batches
    )


def test_unknown_envelope_falls_back_to_fixed_slices(monkeypatch):
    monkeypatch.setattr(automatic, "BATCH_SIZE", 3)
    rows, canonical = document(7)

    batches = automatic.plan_batches(
        list(rows), rows, canonical, 0, "0" * 64, None, None
    )

    assert [len(group) for _, group in batches] == [3, 3, 1]
    assert [evidence_id for _, group in batches for evidence_id in group] == list(rows)


def test_oversize_unit_is_kept_alone_and_never_dropped(monkeypatch):
    monkeypatch.setattr(automatic, "BATCH_SIZE", 3)
    rows, canonical = document(3)
    giant = TextUnit(
        evidence_id="ev_giant",
        page=1,
        kind="paragraph",
        text="nội dung rất dài " * 1200,
        original_text="",
        bbox={},
    )
    rows = {"ev_giant": giant, **rows}
    canonical["pages"][0]["blocks"].insert(
        0, {"evidence_id": giant.evidence_id, "type": "paragraph", "text": giant.text}
    )
    ids = list(rows)
    limits = ModelTokenLimits(max_input_tokens=2500, max_output_tokens=512)

    batches = automatic.plan_batches(ids, rows, canonical, 0, "0" * 64, limits, 512)

    assert batches[0] == (0, ["ev_giant"])
    assert [evidence_id for _, group in batches for evidence_id in group] == ids
