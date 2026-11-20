import json

from qnu.domains.knowledge.index.facts import _classify_row_kind
from qnu.domains.knowledge.index.hybrid import apply_source_diversity
from qnu.domains.knowledge.index.table_layout import CellPosition
from qnu.domains.rag.answer.drafting import parse_answer
from qnu.domains.rag.answer.rewriter import rewrite_contextual_query
from qnu.domains.rag.answer.schemas import EvidenceSource


def test_parse_answer_harmonization_status_answered_with_content():
    """When model outputs substantive statements but keeps insufficient_evidence by momentum,

    parse_answer must harmonize status to answered and clear message.
    """
    sources = [
        EvidenceSource(
            evidence_id="E1",
            chunk_id="c1",
            score=1.0,
            kind="prose",
            text="Nội dung kiểm tra",
            document_id="d1",
            version_id="v1",
            publication_decision_id="p1",
            citations={},
            structure={},
        )
    ]
    raw = {
        "status": "insufficient_evidence",
        "statements": [
            {"text": "Đơn vị chủ trì là P.KT&BĐCL [E1].", "evidence_ids": ["E1"]}
        ],
        "lookups": [],
        "message": "Không tìm thấy thông tin đầy đủ.",
    }
    ans = parse_answer(json.dumps(raw), sources)
    assert ans.status == "answered"
    assert len(ans.statements) == 1
    assert ans.statements[0].text == "Đơn vị chủ trì là P.KT&BĐCL."
    assert ans.statements[0].evidence_ids == ["E1"]
    assert ans.message is None


def test_parse_answer_harmonization_status_answered_without_content():
    """When model outputs status answered but no statements/lookups,

    parse_answer must coerce status to insufficient_evidence.
    """
    sources = [
        EvidenceSource(
            evidence_id="E1",
            chunk_id="c1",
            score=1.0,
            kind="prose",
            text="Nội dung",
            document_id="d1",
            version_id="v1",
            publication_decision_id="p1",
            citations={},
            structure={},
        )
    ]
    raw = {
        "status": "answered",
        "statements": [],
        "lookups": [],
        "message": "Chưa có dữ liệu.",
    }
    ans = parse_answer(json.dumps(raw), sources)
    assert ans.status == "insufficient_evidence"
    assert ans.message == "Chưa có dữ liệu."


def test_classify_row_kind_roman_numeral_group_header():
    """Row with cell 0 as Roman numeral 'I' and cell 1 spanning remainder must be classified as group_header."""
    positions = [
        CellPosition(
            index=0,
            row=1,
            column=0,
            cell={"text": "I", "row_span": 1, "col_span": 1},
        ),
        CellPosition(
            index=1,
            row=1,
            column=1,
            cell={
                "text": "Hoàn thiện Báo cáo tự đánh giá (SAR), minh chứng",
                "row_span": 1,
                "col_span": 5,
            },
        ),
    ]
    kind, banner = _classify_row_kind(row_idx=1, col_count=6, row_positions=positions)
    assert kind == "group_header"
    assert "I. Hoàn thiện Báo cáo tự đánh giá" in banner


def test_rewrite_contextual_query_property_followup():
    """Incomplete follow-up asking about unit/predicate must inherit last_entity and active_document."""
    history = [
        {
            "question": "Theo Kế hoạch 130/KH-ĐHQN, mục 3 nhiệm vụ Hoàn thiện Báo cáo tự đánh giá có mốc thời gian nào?",
            "answer": "Mốc thời gian là từ 20/01 đến 05/02/2026.",
        }
    ]
    q2 = "Đơn vị nào chủ trì và phối hợp?"
    resolved, trace = rewrite_contextual_query(q2, history)
    assert trace["rewritten"] is True
    assert trace["mode"] == "property_followup"
    assert "chủ trì và phối hợp" in resolved
    assert "130/KH-ĐHQN" in resolved


def test_rewrite_contextual_query_conversation_memory_enrichment():
    """When history is empty but conversation_memory has active_document and last_entity,

    rewriter must synthesize query context safely.
    """
    mem = {
        "active_document": "Kế hoạch 130/KH-ĐHQN",
        "last_entity": "nhiệm vụ Hoàn thiện Báo cáo tự đánh giá",
    }
    q = "Đơn vị nào chủ trì và phối hợp?"
    resolved, trace = rewrite_contextual_query(q, history=None, conversation_memory=mem)
    assert trace["rewritten"] is True
    assert "Kế hoạch 130/KH-ĐHQN" in resolved
    assert "nhiệm vụ Hoàn thiện Báo cáo tự đánh giá" in resolved


def test_rewrite_contextual_query_topic_switch_discipline():
    """When follow-up explicitly specifies a new document and entity, it must NOT inherit previous context."""
    history = [
        {
            "question": "Theo Kế hoạch 130/KH-ĐHQN, mục 3 nhiệm vụ Hoàn thiện Báo cáo tự đánh giá có mốc thời gian nào?",
            "answer": "Mốc thời gian là 15/01/2026.",
        }
    ]
    q_new = "Theo Quyết định 4740/QĐ-BGDĐT, tiêu chí 1.1 có bao nhiêu điểm?"
    resolved, trace = rewrite_contextual_query(q_new, history)
    assert trace["rewritten"] is False
    assert resolved == q_new
    assert "130" not in resolved


def test_source_diversity_in_multi_document_pool():
    """When candidates from multiple documents compete for top_k, no single document starves others."""
    class MockHit:
        def __init__(self, chunk_id: str, document_id: str):
            self.chunk_id = chunk_id
            self.document_id = document_id

    # Pool has 10 hits from Doc A and 5 hits from Doc B
    candidates = [MockHit(f"ca_{i}", "doc_A") for i in range(10)] + [
        MockHit(f"cb_{i}", "doc_B") for i in range(5)
    ]
    selected = apply_source_diversity(candidates, count=8)
    assert len(selected) == 8
    doc_counts = {h.document_id: sum(1 for x in selected if x.document_id == h.document_id) for h in selected}
    assert doc_counts["doc_A"] == 4
    assert doc_counts["doc_B"] == 4
