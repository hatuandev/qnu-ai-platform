"""Evidence selection separates retrieval candidates from model evidence."""

from qnu.domains.knowledge.index.schemas import SearchHit
from qnu.domains.rag.answer.selection import VERSION, question_needs, select_hits


def paragraph(index: int, text: str | None = None, **fields) -> SearchHit:
    return SearchHit(
        chunk_id=f"p{index}",
        document_id=fields.pop("document_id", "doc"),
        version_id=fields.pop("version_id", "version"),
        publication_decision_id=fields.pop("publication_decision_id", "published"),
        score=1,
        kind=fields.pop("kind", "paragraph"),
        text=text or f"Generic rule number {index}.",
        citations=fields.pop("citations", {f"run:{index}": {"page": 1}}),
        structure=fields.pop("structure", None),
        **fields,
    )


def context(primary: list[SearchHit], **extra) -> dict:
    return {"primary_ids": [hit.chunk_id for hit in primary], **extra}


def test_question_needs_are_deterministic_and_resolved_marks_follow_up():
    assert question_needs("Chỉ tiêu năm 2024 là bao nhiêu?")["kind"] == "single_value"
    assert question_needs("Điều kiện miễn giảm thế nào?")["kind"] == "condition"
    assert question_needs("Liệt kê các ngành đào tạo")["kind"] == "enumeration"
    assert question_needs("So sánh học phí hai năm")["kind"] == "comparison"
    follow_up = question_needs("Ngành đó bao nhiêu?", "Học phí ngành A bao nhiêu?")
    assert follow_up["follow_up"] is True and follow_up["kind"] == "single_value"


def test_single_value_keeps_tables_required_units_and_distinct_narrative():
    hits = [paragraph(i) for i in range(12)]
    table = paragraph(99, "Bảng chỉ tiêu", kind="table")
    hits.insert(0, table)
    selected, trace = select_hits(
        hits,
        context(hits, added=[{"chunk_id": "p11", "kind": "clause"}]),
        "Chỉ tiêu tuyển sinh năm 2024 là bao nhiêu?",
    )
    ids = [hit.chunk_id for hit in selected]
    assert "p99" in ids and "p11" in ids
    assert trace["version"] == VERSION
    assert trace["selected"]["tables"] == 1
    assert trace["selected_count"] == len(selected)
    assert trace["dropped_count"] == 0
    assert selected == hits


def test_condition_keeps_clause_evidence_beyond_the_narrative_cap():
    hits = [paragraph(i) for i in range(16)]
    selected, trace = select_hits(
        hits,
        context(hits, added=[{"chunk_id": "p15", "kind": "clause"}]),
        "Hồ sơ và điều kiện miễn giảm áp dụng cho trường hợp nào?",
    )
    assert "p15" in [hit.chunk_id for hit in selected]
    assert trace["needs"]["kind"] == "condition"
    assert trace["dropped_count"] == 0


def test_comparison_keeps_an_over_cap_item_with_a_question_term():
    hits = [paragraph(i) for i in range(16)]
    hits[13] = paragraph(13, "Học phí năm 2024 cao hơn năm trước.")
    selected, trace = select_hits(hits, context(hits), "So sánh học phí hai năm gần đây")
    ids = [hit.chunk_id for hit in selected]
    assert trace["needs"]["kind"] == "comparison"
    assert "p13" in ids and "p15" in ids
    assert trace["dropped_count"] == 0


def test_enumeration_keeps_the_whole_retrieved_set():
    hits = [paragraph(i) for i in range(20)]
    selected, trace = select_hits(hits, context(hits), "Liệt kê tất cả các bước")
    assert selected == hits and trace["dropped_count"] == 0


def test_exact_duplicate_is_dropped_only_when_not_required():
    first = paragraph(1, "Same source text.", citations={"run:a": {"page": 1}})
    duplicate = paragraph(2, "Same source text.", citations={"run:a": {"page": 1}})
    selected, trace = select_hits(
        [first, duplicate], context([first, duplicate]), "Quy định chung là gì?"
    )
    assert [hit.chunk_id for hit in selected] == ["p1"]
    assert trace["dropped"] == [{"chunk_id": "p2", "kind": "paragraph", "reason": "duplicate"}]
    kept, _ = select_hits(
        [first, duplicate],
        context([first, duplicate], support_ids=["p2"]),
        "Quy định chung là gì?",
    )
    assert [hit.chunk_id for hit in kept] == ["p1", "p2"]


def test_follow_up_uses_resolved_terms_for_the_overlap_allowance():
    hits = [paragraph(i) for i in range(10)]
    hits[8] = paragraph(8, "Học phí ngành Kỹ thuật phần mềm là 20 triệu.")
    selected, trace = select_hits(
        hits,
        context(hits),
        "Ngành đó học phí bao nhiêu?",
        resolved_question="Học phí ngành Kỹ thuật phần mềm năm 2024 là bao nhiêu?",
    )
    ids = [hit.chunk_id for hit in selected]
    assert "p8" in ids and "p9" in ids
    assert trace["needs"]["follow_up"] is True
    assert trace["dropped"] == []
