"""P1 retrieval: phrase lexical recall, anchor coverage and rerank-order selection."""

from qnu.domains.knowledge.index.hybrid import (
    exact_anchors,
    fuse,
    lexical_expression,
    select_reranked,
)
from qnu.domains.knowledge.index.schemas import SearchHit


def hit(chunk_id: str, text: str | None = None) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        document_id="doc",
        version_id="ver",
        publication_decision_id="pub",
        score=0.0,
        kind="paragraph",
        text=text if text is not None else chunk_id,
        citations={},
        structure=None,
    )


def test_phrase_expression_uses_adjacent_pairs_once():
    assert (
        lexical_expression("Tổng số lượng tuyển sinh", phrases=True)
        == '"Tổng số" OR "số lượng" OR "lượng tuyển" OR "tuyển sinh"'
    )
    assert lexical_expression("Chỉ tiêu", phrases=True) == '"Chỉ tiêu"'
    assert lexical_expression("Chỉ tiêu") == '"Chỉ" OR "tiêu"'
    assert lexical_expression("!!!", phrases=True) == ""


def test_weighted_fuse_keeps_candidates_from_every_branch():
    first, second, third = hit("a"), hit("b"), hit("c")
    fused = fuse([[first, second], [second, third]], 3, 60, weights=[1.0, 2.0])
    assert [h.chunk_id for h in fused] == ["b", "c", "a"]
    assert fused[0].score == 1 / 62 + 2 / 61
    assert first.score == 0.0


def test_exact_anchors_keep_identifier_and_leading_zero_code_only():
    assert exact_anchors("chương trình Kế toán số mã AM-0029 năm 2027") == ["am-0029"]
    assert exact_anchors("ngành 0120 và 2027") == ["0120"]
    assert exact_anchors("năm 2027") == []


def test_anchor_candidate_survives_the_fusion_cut():
    dense = [hit(f"d{rank:02d}") for rank in range(1, 11)]
    lexical = [hit(f"l{rank:02d}") for rank in range(1, 26)]
    target = hit("target", "row[12]: AM-0029 | Kế toán số | 2027 | 127")
    lexical.append(target)
    fused = fuse(
        [dense, lexical],
        10,
        60,
        anchors=exact_anchors("mã AM-0029 năm 2027"),
    )
    assert len(fused) == 10
    assert fused[-1].chunk_id == "target"


def test_anchor_reservation_never_duplicates_a_selected_candidate():
    dense = [hit("target", "AM-0029"), *[hit(f"d{rank:02d}") for rank in range(2, 11)]]
    lexical = [hit(f"l{rank:02d}") for rank in range(1, 26)]
    fused = fuse([dense, lexical], 10, 60, anchors=["am-0029"])
    assert [h.chunk_id for h in fused].count("target") == 1


def test_rerank_order_is_authoritative_over_the_base_prior():
    # Q13 regression: the formula chunk is cross-encoder rank 2 but base fusion
    # rank 9. A second weighted RRF put it outside top 5; the reranker order wins.
    fusion = [hit(f"c{rank:02d}") for rank in range(1, 11)]
    reranked = [
        hit("c06"),
        hit("c09"),
        hit("c01"),
        hit("c02"),
        hit("c03"),
        hit("c04"),
        hit("c05"),
        hit("c07"),
        hit("c08"),
        hit("c10"),
    ]
    selected = select_reranked(fusion, reranked, 5)
    assert [h.chunk_id for h in selected] == ["c06", "c09", "c01", "c02", "c03"]
