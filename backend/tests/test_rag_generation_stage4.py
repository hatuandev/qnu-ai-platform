"""Generation/status boundary checks, not a live-model accuracy benchmark."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from app.modules.rag.service import RagService, is_refusal_answer


@pytest.mark.parametrize("has_evidence", [True, False])
def test_related_evidence_cannot_override_an_explicit_non_answer(has_evidence):
    assert is_refusal_answer("Không tìm thấy thông tin điểm sàn cho năm được hỏi.", has_evidence)


@pytest.mark.asyncio
@pytest.mark.parametrize("answer,has_citation,expected", [
    ("Không tìm thấy thông tin điểm sàn cho năm được hỏi.", True, "insufficient_context"),
    ("Chương trình học có thực hành.", False, "insufficient_context"),
    ("Chương trình học có thực hành.", True, "answered"),
    ("Chương trình học có thực hành.\n\n[GỢI Ý]:\n- Không tìm thấy thông tin thì liên hệ ở đâu?",
     True, "answered"),
])
async def test_status_and_cache_follow_visible_answer_not_citation_presence(answer, has_citation, expected):
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="c", tenant_id="t", workspace_id="w",
                                 binding_revisions={"b": "i"})
    candidate = FusionCandidate("chunk", "b", "Chương trình học có thực hành.", 0.1)
    service = RagService()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={})
    with (patch("app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot)),
          patch("app.modules.rag.service.fact_layer.lookup_facts", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.hybrid_retriever.retrieve", AsyncMock(return_value=[candidate])),
          patch("app.modules.rag.service.hybrid_retriever.expand_with_neighbors", AsyncMock(return_value={})),
          patch("app.modules.rag.service.load_row_anchors", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.semantic_cache.get", AsyncMock(return_value=None)),
          patch("app.modules.rag.service.semantic_cache.set", AsyncMock()) as cache,
          # This test isolates status/cache presentation; the independent semantic
          # boundary has its own real contract tests in test_rag_batch_492.
          patch("app.modules.rag.response_audit.audit_visible_answer", AsyncMock(
              return_value={"accepted": True, "candidate_ids": ["chunk"]})),
          patch.object(service, "_generate_answer_with_fallback", AsyncMock(return_value=answer))):
        from app.modules.rag.schemas import Citation

        cites = [Citation(source_id="b", title="Source", quote=candidate.content)] if has_citation else []
        with patch("app.modules.rag.service.citation_guard.filter_evidence_citations", return_value=cites):
            response = await service.ask(db, AskRequest(question="Nội dung chương trình?", collection_id="c"))
    assert response.status == expected
    assert "[GỢI Ý]" not in response.answer
    assert cache.await_count == (1 if expected == "answered" else 0)
    if not has_citation:
        assert "Chương trình học có thực hành." not in response.answer
        assert response.suggested_questions == []


@pytest.mark.asyncio
async def test_grounding_instruction_augments_custom_persona_without_changing_model():
    service = RagService()
    req = AskRequest(question="Điểm đầu vào?", collection_id="c", system_prompt="CUSTOM PERSONA",
                     preferred_model_name="arbitrary/new-model", preferred_provider_id="provider", max_tokens=5000)
    with patch("app.modules.rag.service.modelops_service.generate", AsyncMock(
            return_value=SimpleNamespace(content="Source-based answer"))) as generate:
        from app.modules.modelops.schemas import ChatMessage

        await service._generate_answer_with_fallback(AsyncMock(), req,
            [ChatMessage(role="system", content=req.system_prompt), ChatMessage(role="user", content="Question and source")],
            0.2, "", [])
    sent = generate.call_args.args[1]
    assert sent.messages[0].content.startswith(req.system_prompt)
    assert "TƯƠNG ĐƯƠNG NGỮ NGHĨA" in sent.messages[0].content
    assert "CHỈ RÕ PHẦN THIẾU" in sent.messages[0].content
    assert sent.preferred_model_name == req.preferred_model_name
    assert sent.preferred_provider_id == req.preferred_provider_id
    assert sent.max_tokens == 5000 and req.system_prompt == "CUSTOM PERSONA"
