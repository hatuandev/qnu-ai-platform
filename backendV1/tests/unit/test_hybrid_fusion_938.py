"""P1 retrieval: phrase lexical recall and weighted fusion over every branch."""

from qnu.domains.knowledge.index.hybrid import (
    RERANK_RRF_K,
    RERANK_WEIGHT,
    fuse,
    lexical_expression,
)
from qnu.domains.knowledge.index.schemas import SearchHit


def hit(chunk_id: str) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        document_id="doc",
        version_id="ver",
        publication_decision_id="pub",
        score=0.0,
        kind="paragraph",
        text=chunk_id,
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


def test_rerank_fusion_surfaces_strong_cross_encoder_candidate():
    # Q27 regression: the cross-encoder ranks the answer chunk #2 but base fusion
    # ranks it #16. Reusing the base RRF k=60 let a #6/#6 competitor win on the
    # rank-only prior; RERANK_RRF_K sharpens the reranker so the chunk surfaces.
    fusion = [hit(f"c{i:02d}") for i in range(1, 31)]
    rerank = [
        hit(c)
        for c in (
            "c02", "c16", "c07", "c01", "c04", "c06", "c19", "c03", "c26", "c24",
            "c17", "c10", "c05", "c22", "c09", "c20", "c12", "c21", "c11", "c25",
            "c08", "c15", "c13", "c14", "c29", "c28", "c18", "c23", "c27", "c30",
        )
    ]
    target = "c16"
    old = fuse([fusion, rerank], 5, 60, weights=[1.0, RERANK_WEIGHT])
    assert target not in [h.chunk_id for h in old]
    new = fuse([fusion, rerank], 5, RERANK_RRF_K, weights=[1.0, RERANK_WEIGHT])
    assert target in [h.chunk_id for h in new]
