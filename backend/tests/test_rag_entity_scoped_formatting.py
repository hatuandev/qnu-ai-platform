"""Tests for Entity-Scoped Extraction, Sanitization and Dynamic Formatting in RAG."""

from __future__ import annotations

import pytest

from app.modules.rag.composer import (
    answer_format_planner,
    sanitize_rag_answer,
)
from app.modules.rag.query_router import query_classifier


def test_sanitize_rag_answer_removes_pipe_clusters():
    """Verify raw OCR pipe clusters are cleaned up."""
    raw = "|||||| (Toán, Anh, Sử) || Một số thông tin tuyển sinh |||"
    cleaned = sanitize_rag_answer(raw)
    assert "|||" not in cleaned
    assert "Một số thông tin tuyển sinh" in cleaned


def test_sanitize_rag_answer_formats_target_entity_row():
    """Verify multi-major raw table dumps are safely distilled down to the requested entity."""
    raw_dump = (
        "Chào bạn! Dựa trên tài liệu chính thức của Trường Đại học Quy Nhơn, mình xin giải đáp như sau:\n\n"
        "|||||| (Toán, Anh, Sử) || 31 | 7380101 | Luật | 1,2,3,4 || (Văn, Toán, Anh) || "
        "36 | 7480201 | Công nghệ thông tin (An toàn, an ninh mạng) | 1,2,3,4 || (Toán, Anh, Lý) (Toán, Anh, Tin) || "
        "37 | 7480107 | Trí tuệ nhân tạo | 1,2,3,4 || (Toán, Lý, Hóa) |"
    )
    cleaned = sanitize_rag_answer(raw_dump, target_entity="Công nghệ thông tin")

    # Must contain target major
    assert "Công Nghệ Thông Tin" in cleaned
    assert "Phương thức 1,2,3,4" in cleaned
    assert "(Toán, Anh, Lý)" in cleaned
    assert "(Toán, Anh, Tin)" in cleaned

    # Must NOT contain unrelated majors from raw dump
    assert "7380101" not in cleaned
    assert "Luật" not in cleaned
    assert "Trí tuệ nhân tạo" not in cleaned
    assert "||||||" not in cleaned


def test_sanitize_rag_answer_preserves_valid_markdown_table():
    """Verify valid markdown tables are preserved intact without mangling pipes."""
    table = (
        "| STT | Mã ngành | Tên ngành |\n"
        "|---|---|---|\n"
        "| 1 | 7480201 | Công nghệ thông tin |"
    )
    cleaned = sanitize_rag_answer(table)
    assert "| STT | Mã ngành | Tên ngành |" in cleaned
    assert "| 1 | 7480201 | Công nghệ thông tin |" in cleaned


def test_query_classifier_extracts_target_entities():
    """Verify QueryClassifier extracts target entity for canonical majors and phrases."""
    analysis = query_classifier.analyze(
        "bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?",
        module_code="admissions",
    )
    assert "Công Nghệ Thông Tin" in analysis.target_entities
    assert "7480201" in analysis.entity_codes


def test_format_planner_instructions():
    """Verify AnswerFormatPlanner generates clear presentation directives."""
    instructions_combo = answer_format_planner.get_format_instructions(
        "bullet_list",
        target_entity="Công Nghệ Thông Tin",
        is_combo_query=True,
    )
    assert "tổ hợp môn xét tuyển" in instructions_combo
    assert "Công Nghệ Thông Tin" in instructions_combo
    assert "Tuyệt đối KHÔNG sao chép" in instructions_combo

    instructions_table = answer_format_planner.get_format_instructions("markdown_table")
    assert "BẢNG MARKDOWN" in instructions_table


@pytest.mark.asyncio
async def test_rag_service_entity_scoped_prompt_assembly():
    """Verify RagService injects entity-scoped constraint when a major is identified."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.modules.modelops.schemas import LLMGenerateResponse
    from app.modules.rag.schemas import AskRequest
    from app.modules.rag.service import rag_service

    mock_db = AsyncMock()

    # Mock retriever candidates containing multi-major raw text
    mock_candidate = MagicMock()
    mock_candidate.chunk_id = "chunk_multi_1"
    mock_candidate.document_id = "doc_multi_1"
    mock_candidate.page_number = 15
    mock_candidate.content = (
        "|| 31 | 7380101 | Luật | 1,2,3,4 || "
        "36 | 7480201 | Công nghệ thông tin | 1,2,3,4 || (Toán, Anh, Lý) (Toán, Anh, Tin) ||"
    )
    mock_candidate.score = 0.95
    mock_candidate.document_title = "Đề án Tuyển sinh 2026"
    mock_candidate.section = "Đề án Tuyển sinh 2026"
    mock_candidate.metadata = {"chunk_index": 15}

    with patch("app.modules.rag.service.semantic_cache.get", new_callable=AsyncMock, return_value=None), \
         patch("app.modules.rag.service.hybrid_retriever.retrieve", new_callable=AsyncMock) as mock_ret, \
         patch("app.modules.rag.service.hybrid_retriever.expand_with_neighbors", new_callable=AsyncMock) as mock_exp, \
         patch("app.modules.rag.service.fact_layer.lookup_facts", new_callable=AsyncMock) as mock_facts, \
         patch("app.modules.rag.service.modelops_service.generate", new_callable=AsyncMock) as mock_llm:

        mock_ret.return_value = [mock_candidate]
        mock_exp.return_value = {}
        mock_facts.return_value = []
        mock_llm.return_value = LLMGenerateResponse(
            content=(
                "Chào bạn! Ngành Công nghệ thông tin xét tuyển các tổ hợp:\n"
                "- (Toán, Anh, Lý)\n"
                "- (Toán, Anh, Tin)\n"
                "Áp dụng cho các phương thức xét tuyển 1, 2, 3 và 4."
            ),
            provider="test-provider",
            model="test-model",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=120,
        )

        req = AskRequest(
            question="bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?",
            collection_id="col_admissions",
            module_code="admissions",
            conversation_id="conv_test_entity",
        )

        resp = await rag_service.ask(mock_db, req)

        assert resp.status == "answered"
        assert "Công nghệ thông tin" in resp.answer
        assert "Luật" not in resp.answer

        # Verify the prompt sent to LLM contains the entity constraint
        sent_llm_req = mock_llm.call_args[0][1]
        user_msg = [m for m in sent_llm_req.messages if m.role == "user"][-1].content
        assert "RÀNG BUỘC TRÍCH XUẤT THEO THỰC THỂ" in user_msg
        assert "Công Nghệ Thông Tin" in user_msg
        assert "CHỈ ĐƯỢC PHÉP trích xuất" in user_msg


def test_interrogative_pronoun_nganh_nao_has_no_target_entities():
    """Questions like 'áp dụng cho những ngành nào' must NOT treat 'Nào' as a major entity."""
    analysis = query_classifier.analyze(
        "Phương thức xét tuyển học bạ của trường áp dụng cho những ngành nào?",
        module_code="admissions",
    )
    assert len(analysis.target_entities) == 0
    assert "Nào" not in analysis.target_entities

