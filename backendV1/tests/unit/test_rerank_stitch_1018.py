"""Paragraph fragments split by OCR line breaks reach the reranker as one sentence."""

import hashlib
import json

from qnu.domains.knowledge.index.presentation import (
    PRESENTATION_VERSION,
    paragraph_body,
    paragraph_title,
    rerank_text,
    stitch_window,
)
from qnu.domains.knowledge.index.schemas import SearchHit


def enriched(kind: str, body: str, title: str = "Thông tin TSĐH", heading: str = "2. Cũ:"):
    envelope = json.dumps(
        {"version": "qnu.search-context/v1", "title": title, "heading": heading, "units": []},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    original = f"{title}\n{heading}\n{body}"
    text = envelope + "\n" + original
    structure = {
        "search_context": {
            "version": "qnu.search-context/v1",
            "original_text": original,
            "original_sha256": hashlib.sha256(original.encode()).hexdigest(),
            "prefix": envelope + "\n",
            "glossary": [],
        }
    }
    return SearchHit(
        chunk_id="ic_1",
        document_id="cdoc_1",
        version_id="cver_1",
        publication_decision_id="pdec_1",
        score=0.5,
        kind=kind,
        text=text,
        citations={},
        structure=structure,
    )


def test_paragraph_body_drops_repeated_title_and_inherited_heading():
    hit = enriched("paragraph", "một mảnh câu,")
    assert paragraph_body(hit.kind, hit.text, hit.structure) == "một mảnh câu,"
    assert paragraph_title(hit.structure) == "Thông tin TSĐH"
    assert paragraph_body("table", hit.text, hit.structure) is None
    # Without enrichment nothing is stitched; old rerank_text stays as before.
    plain = SearchHit(**{**hit.model_dump(), "structure": {"context": {}}})
    assert paragraph_body(plain.kind, plain.text, plain.structure) is None
    assert rerank_text(plain) == " ".join(plain.text.split())


def test_stitch_window_completes_the_sentence_around_the_anchor():
    bodies = {
        59: "Thông tin TSĐH cập nhật",
        60: "3. Quy tắc quy đổi tương đương ngưỡng đầu vào",
        61: "và điểm trúng tuyển: thông báo sau khi có kết quả thi.",
        70: "4. Mục mới:",
        71: "nội dung mục mới.",
    }
    expected = (
        "Thông tin TSĐH cập nhật 3. Quy tắc quy đổi tương đương ngưỡng đầu vào "
        "và điểm trúng tuyển: thông báo sau khi có kết quả thi."
    )
    assert stitch_window(bodies, 60) == expected
    # From inside item 3 the walk stops where the item starts, not before it.
    assert stitch_window(bodies, 61) == (
        "3. Quy tắc quy đổi tương đương ngưỡng đầu vào "
        "và điểm trúng tuyển: thông báo sau khi có kết quả thi."
    )
    # A fragment that already ends its sentence is never extended.
    assert stitch_window(bodies, 71) is None


def test_numbered_item_is_included_then_ends_the_backward_walk():
    bodies = {1: "2. Kết thúc mục cũ.", 2: "3. Mở đầu mục mới", 3: "phần còn lại."}
    assert stitch_window(bodies, 3) == "3. Mở đầu mục mới phần còn lại."


def test_windows_stay_bounded_by_parts_and_bytes():
    parts = {i: f"mảnh {i}," for i in range(20)}
    parts[13] = "kết thúc."
    window = stitch_window(parts, 10)
    assert window == "mảnh 8, mảnh 9, mảnh 10, mảnh 11,"
    huge = {1: "a" * 500, 2: "b" * 400, 3: "c" * 10}
    assert stitch_window(huge, 1) is None


def test_version_marks_the_new_rerank_reading():
    assert PRESENTATION_VERSION == "qnu.evidence-reading/v3"
    assert rerank_text(enriched("paragraph", "một mảnh câu,")).endswith("một mảnh câu,")
