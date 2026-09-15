"""RAG Service — Complete Query, Hybrid Retrieval, Fact Layer & Answer Composition Pipeline."""

from __future__ import annotations

import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guardrails import input_guardrail, output_guardrail
from app.core.redis import semantic_cache
from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.composer import answer_format_planner
from app.modules.rag.facts import fact_layer
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import (
    AskRequest,
    AskResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

logger = logging.getLogger(__name__)


class RagService:
    """Service orchestrating Hybrid Retrieval, Fact verification and RAG response generation."""

    async def search(self, db: AsyncSession, req: SearchRequest) -> SearchResponse:
        start_time = time.perf_counter()

        candidates = await hybrid_retriever.retrieve(
            db=db,
            collection_id=req.collection_id,
            query=req.query,
            top_k=req.top_k,
            rerank_top_k=req.rerank_top_k,
        )

        items = [
            SearchResultItem(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                content=c.content,
                score=round(c.rrf_score, 4),
                rank=idx,
                section=c.section,
                page_number=c.page_number,
                metadata=c.metadata or {},
            )
            for idx, c in enumerate(candidates, start=1)
        ]

        exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return SearchResponse(
            query=req.query,
            collection_id=req.collection_id,
            total_found=len(items),
            items=items,
            execution_time_ms=exec_ms,
        )

    async def ask(self, db: AsyncSession, req: AskRequest) -> AskResponse:
        start_time = time.perf_counter()

        # 1. Input Guardrail safety check (Prompt Injection)
        guard_res = input_guardrail.check(req.question)
        if not guard_res.is_safe:
            return AskResponse(
                status="insufficient_context",
                answer=f"Yêu cầu của bạn không thể xử lý: {guard_res.reason}",
                answer_format="paragraph",
                citations=[],
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 2. Check Semantic Cache
        cached = await semantic_cache.get(req.collection_id, req.question)
        if cached:
            logger.info("Semantic cache HIT for query='%s'", req.question[:30])
            cached["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            return AskResponse.model_validate(cached)

        # 3. Lookup Structured Fact Layer (Extract numerical facts)
        keywords = [w.strip() for w in req.question.split() if len(w.strip()) >= 3]
        facts = await fact_layer.lookup_facts(db, req.collection_id, keywords=keywords, limit=5)
        fact_markdown = fact_layer.format_facts_as_markdown(facts)

        # 4. Hybrid Retrieval (Dense + Sparse + Rerank)
        candidates = await hybrid_retriever.retrieve(
            db=db,
            collection_id=req.collection_id,
            query=req.question,
            top_k=8,
            rerank_top_k=5,
        )

        # 5. No-Answer Policy if context is empty
        if not candidates and not facts:
            no_answer_text = citation_guard.get_no_answer_response(req.module_code)
            return AskResponse(
                status="insufficient_context",
                answer=no_answer_text,
                answer_format="paragraph",
                citations=[],
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 6. Format Planning
        chosen_format = answer_format_planner.plan_format(
            req.question,
            context_has_table=bool(
                facts or any("table" in (c.content or "").lower() for c in candidates)
            ),
        )

        # 7. Assemble Prompt & Generate Answer (Mock/LLM generation)
        context_texts = [c.content for c in candidates]
        full_prompt = answer_format_planner.assemble_prompt(
            query=req.question,
            context_chunks=context_texts,
            fact_table=fact_markdown,
            custom_system_prompt=req.system_prompt,
        )
        logger.debug("Assembled prompt for query '%s' (length: %d)", req.question, len(full_prompt))

        # Build answer synthesis
        citations = citation_guard.build_citations(candidates)

        # When structured facts are available, incorporate directly into answer
        if fact_markdown:
            synthesized_answer = (
                f"Dựa trên dữ liệu chính thức của Trường Đại học Quy Nhơn, mình xin gửi thông tin chi tiết đến bạn:\n\n"
                f"{fact_markdown}\n\n"
                f"**Thông tin bổ sung:**\n"
                f"{candidates[0].content[:400] if candidates else ''}\n\n"
                f"---\n"
                f"*Bạn có thể muốn tìm hiểu thêm:*\n"
                f"- Phương thức xét tuyển học bạ của ngành này như thế nào?\n"
                f"- Cơ hội việc làm sau khi tốt nghiệp ra sao?"
            )
        else:
            main_chunk = candidates[0].content if candidates else ""
            synthesized_answer = (
                f"Chào bạn! Dựa trên tài liệu chính thức của Trường Đại học Quy Nhơn, mình xin giải đáp như sau:\n\n"
                f"{main_chunk}\n\n"
                f"---\n"
                f"*Bạn có thể muốn tìm hiểu thêm:*\n"
                f"- Các mốc thời gian nộp hồ sơ quan trọng trong năm?\n"
                f"- Học phí và chính sách miễn giảm cho sinh viên?"
            )

        # 8. Output Guardrail safety check
        safe_output = output_guardrail.check(synthesized_answer)
        final_answer = safe_output.sanitized_text

        exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
        resp = AskResponse(
            status="answered",
            answer=final_answer,
            answer_format=chosen_format,
            citations=citations,
            facts_used=[
                {"entity": f.entity_name, "attr": f.attribute_name, "val": f.attribute_value}
                for f in facts
            ],
            latency_ms=exec_ms,
        )

        # 9. Save to Semantic Cache
        await semantic_cache.set(req.collection_id, req.question, resp.model_dump())

        return resp


rag_service = RagService()
