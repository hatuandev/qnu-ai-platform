"""RAG Service — Complete Query, Hybrid Retrieval, Fact Layer & Answer Composition Pipeline."""

from __future__ import annotations

import logging
import re
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guardrails import input_guardrail, output_guardrail
from app.core.redis import semantic_cache
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.composer import (
    answer_format_planner,
    build_generic_system_instruction,
    extract_suggested_questions,
    sanitize_rag_answer,
)
from app.modules.rag.facts import fact_layer
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.query_router import (
    QueryAnalysis,
    QueryIntent,
    query_classifier,
    scope_history_by_topic,
)
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import (
    AskRequest,
    AskResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

logger = logging.getLogger(__name__)


REFUSAL_PHRASES = (
    "thông tin này hiện chưa có",
    "chưa có trong tài liệu chính thức",
    "chưa có dữ liệu chính thức",
    "tài liệu không cung cấp",
    "đề án không cung cấp",
    "không tìm thấy thông tin",
)


def is_refusal_answer(answer: str, has_evidence: bool) -> bool:
    """Detect No-Answer refusals without domain-specific keyword bias."""
    if has_evidence:
        return False
    lowered = answer.lower()
    return any(phrase in lowered for phrase in REFUSAL_PHRASES)


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
            tenant_id=req.tenant_id,
            workspace_id=req.workspace_id,
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

        # 2. Check Semantic Cache (history-aware; skipped for context-dependent shorts)
        history_list = req.history if isinstance(req.history, list) else []
        question_word_count = len(re.findall(r"\w+", req.question or ""))
        is_context_dependent = bool(history_list) and question_word_count < 8
        history_hash = semantic_cache.hash_history(history_list) if history_list else None
        if is_context_dependent:
            logger.debug(
                "Semantic cache skipped for context-dependent query='%s'",
                req.question[:30],
            )
            cached = None
        else:
            cached = await semantic_cache.get(
                req.collection_id,
                req.question,
                req.preferred_model_name or "default",
                tenant_id=req.tenant_id,
                workspace_id=req.workspace_id,
                history_hash=history_hash,
            )
        if cached:
            logger.info("Semantic cache HIT for query='%s'", req.question[:30])
            cached["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            cached["answer"] = sanitize_rag_answer(cached.get("answer", ""))
            return AskResponse.model_validate(cached)

        # 3. Query Intent Analysis & Fact-First Routing (module-aware, reusable)
        analysis = query_classifier.analyze(req.question, module_code=req.module_code)
        lookup_limit = 10 if analysis.intent == QueryIntent.EXACT_FACT else 5

        facts = await fact_layer.lookup_facts(
            db,
            req.collection_id,
            keywords=analysis.keywords,
            entity_codes=analysis.entity_codes if analysis.entity_codes else None,
            fact_attributes=analysis.fact_attributes if analysis.fact_attributes else None,
            limit=lookup_limit,
            tenant_id=req.tenant_id,
            workspace_id=req.workspace_id,
            subject_names=analysis.subject_names if analysis.subject_names else None,
            target_entities=analysis.target_entities if analysis.target_entities else None,
        )
        fact_markdown = fact_layer.format_facts_as_markdown(facts)

        # 4. Hybrid Retrieval with Intent-tailored Top-K and RRF weights.
        # EXACT_FACT trusts lexical precision (codes, quotas); NARRATIVE leans on semantics.
        if analysis.intent == QueryIntent.EXACT_FACT:
            retrieval_top_k = 8
            rerank_top_k = 6
            dense_weight, sparse_weight = 1.0, 1.2
        elif analysis.intent == QueryIntent.MIXED:
            retrieval_top_k = 12
            rerank_top_k = 8
            dense_weight, sparse_weight = 1.0, 1.0
        else:
            retrieval_top_k = 12
            rerank_top_k = 8
            dense_weight, sparse_weight = 1.2, 0.8
        logger.debug(
            "Retrieval policy intent=%s top_k=%d rerank_top_k=%d dense_w=%.1f sparse_w=%.1f",
            analysis.intent,
            retrieval_top_k,
            rerank_top_k,
            dense_weight,
            sparse_weight,
        )

        # Augment retrieval query with detected entity codes (e.g. program codes 7480201)
        retrieval_query = req.question
        if analysis.entity_codes:
            extra_tokens = [c for c in analysis.entity_codes if c not in retrieval_query]
            if extra_tokens:
                retrieval_query = f"{retrieval_query} {' '.join(extra_tokens)}"

        # Keyword-form variant for multi-query sparse fusion (cheap, no extra embedding).
        keyword_parts = list(analysis.entity_codes) + list(analysis.subject_names)
        keyword_parts += [kw for kw in analysis.keywords if len(kw.strip()) >= 6]
        keyword_query = " ".join(dict.fromkeys(keyword_parts))
        sparse_variants = (
            [keyword_query]
            if keyword_query and keyword_query.strip().lower() not in retrieval_query.strip().lower()
            else []
        )

        candidates = await hybrid_retriever.retrieve(
            db=db,
            collection_id=req.collection_id,
            query=retrieval_query,
            top_k=retrieval_top_k,
            rerank_top_k=rerank_top_k,
            tenant_id=req.tenant_id,
            workspace_id=req.workspace_id,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
            sparse_variants=sparse_variants,
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

        # 4b. Parent-style neighbor expansion (prompt-only background, never cited)
        neighbor_context = await hybrid_retriever.expand_with_neighbors(
            db,
            candidates,
            req.collection_id,
            window=1,
            max_expansions=2,
        )

        # 6. Format Planning
        chosen_format = answer_format_planner.plan_format(
            req.question,
            context_has_table=bool(
                facts or any("table" in (c.content or "").lower() for c in candidates)
            ),
        )

        # 7. Assemble Prompt & Generate Answer via ModelOps LLM Runtime
        context_texts = [c.content for c in candidates]
        for neighbors in (neighbor_context or {}).values():
            for n_text in neighbors:
                if n_text and n_text not in context_texts:
                    context_texts.append(n_text)

        citations = citation_guard.build_citations(candidates)
        system_instruction = build_generic_system_instruction(req.module_code, req.system_prompt)

        # Tiered evidence: fact-first queries rank facts above chunks above history.
        # Deterministic decoding keeps figures stable for exact lookups.
        is_fact_query = analysis.is_fact_first
        fact_temperature = min(req.temperature, 0.2) if is_fact_query else req.temperature

        target_entity_str = (
            ", ".join(analysis.target_entities)
            if hasattr(analysis, "target_entities") and analysis.target_entities
            else None
        )

        is_combo_query = bool(
            analysis.subject_names or any(k in req.question.lower() for k in ("môn", "tổ hợp"))
        )

        user_content = answer_format_planner.build_rag_user_prompt(
            question=req.question,
            chosen_format=chosen_format,
            target_entity=target_entity_str,
            is_combo_query=is_combo_query,
            is_fact_query=is_fact_query,
            fact_markdown=fact_markdown,
            context_texts=context_texts,
            neighbor_context=neighbor_context,
        )

        # Topic-scoped history: independent new questions must not inherit stale answers.
        llm_messages = self._build_chat_messages(
            system_instruction=system_instruction,
            user_content=user_content,
            history_list=history_list,
            analysis=analysis,
        )

        synthesized_answer = await self._generate_answer_with_fallback(
            db=db,
            req=req,
            llm_messages=llm_messages,
            temperature=fact_temperature,
            fact_markdown=fact_markdown,
            candidates=candidates,
        )

        # 8. Output Guardrail safety check
        safe_output = output_guardrail.check(synthesized_answer)
        final_answer = safe_output.sanitized_text

        # Evidence-based citation filtering (generic, no domain keyword bias)
        final_citations = citation_guard.filter_evidence_citations(citations, final_answer)

        facts_used_payload = [
            {"entity": f.entity_name, "attr": f.attribute_name, "val": f.attribute_value}
            for f in facts
        ]
        has_evidence = bool(final_citations or facts_used_payload)
        refusal_detected = is_refusal_answer(final_answer, has_evidence)
        status = "insufficient_context" if refusal_detected else "answered"
        clean_answer, suggested_questions = extract_suggested_questions(
            final_answer, current_query=req.question
        )

        # Sanitize answer from broken table pipes or verbatim multi-major dumps
        clean_answer = sanitize_rag_answer(clean_answer, target_entity=target_entity_str)

        # Numeric grounding gate: multi-digit figures in the answer must exist in evidence.
        if status == "answered":
            numeric_ok, ungrounded_numbers = citation_guard.verify_numeric_grounding(
                clean_answer,
                final_citations,
                facts_used_payload,
                query=req.question,
                system_context=req.system_prompt,
                candidate_texts=[c.content for c in candidates],
            )
            if not numeric_ok:
                logger.warning(
                    "Numeric grounding failed for query='%s': ungrounded=%s",
                    req.question[:50],
                    ungrounded_numbers,
                )
                status = "insufficient_context"
                clean_answer = citation_guard.get_no_answer_response(req.module_code)
                final_citations = []
                suggested_questions = []

        exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
        resp = AskResponse(
            status=status,
            answer=clean_answer,
            answer_format=chosen_format,
            citations=final_citations,
            facts_used=facts_used_payload,
            suggested_questions=suggested_questions,
            latency_ms=exec_ms,
        )

        # 9. Save to Semantic Cache (Only cache valid answered queries with citations)
        if status == "answered" and final_citations and not is_context_dependent:
            await semantic_cache.set(
                req.collection_id,
                req.question,
                resp.model_dump(),
                req.preferred_model_name or "default",
                tenant_id=req.tenant_id,
                workspace_id=req.workspace_id,
                history_hash=history_hash,
            )

        return resp

    @staticmethod
    def _build_chat_messages(
        system_instruction: str,
        user_content: str,
        history_list: list[dict],
        analysis: QueryAnalysis,
    ) -> list[ChatMessage]:
        """Format multi-turn conversation messages with topic scoping and tier labeling."""
        scoped_history = scope_history_by_topic(history_list, analysis)
        llm_messages = [ChatMessage(role="system", content=system_instruction)]
        for h_msg in scoped_history:
            h_role = h_msg.get("role", "user")
            h_text = h_msg.get("content", "")
            if h_role in ("user", "assistant") and h_text:
                if analysis.is_fact_first:
                    h_text = f"[TẦNG 3 - Lịch sử trao đổi, chỉ tham khảo ngữ cảnh] {h_text}"
                llm_messages.append(ChatMessage(role=h_role, content=h_text))
        llm_messages.append(ChatMessage(role="user", content=user_content))
        return llm_messages

    async def _generate_answer_with_fallback(
        self,
        db: AsyncSession,
        req: AskRequest,
        llm_messages: list[ChatMessage],
        temperature: float,
        fact_markdown: str | None,
        candidates: list[FusionCandidate],
    ) -> str:
        """Call ModelOps LLM with primary model, fallback model, or grounded context synthesis."""
        try:
            llm_req = LLMGenerateRequest(
                messages=llm_messages,
                temperature=temperature,
                max_tokens=req.max_tokens,
                thinking_budget=req.thinking_budget,
                conversation_id=req.conversation_id,
                preferred_provider_id=req.preferred_provider_id,
                preferred_model_name=req.preferred_model_name,
                fallback_model_name=req.fallback_model,
            )
            llm_res = await modelops_service.generate(db, llm_req)
            return llm_res.content.strip()
        except Exception as e:
            logger.warning(
                "ModelOps primary model '%s' generation failed (%s). Checking fallback model...",
                req.preferred_model_name,
                e,
            )

        if req.fallback_model and req.fallback_model != req.preferred_model_name:
            try:
                fallback_llm_req = LLMGenerateRequest(
                    messages=llm_messages,
                    temperature=temperature,
                    max_tokens=req.max_tokens,
                    thinking_budget=req.thinking_budget,
                    conversation_id=req.conversation_id,
                    preferred_provider_id=req.preferred_provider_id,
                    preferred_model_name=req.fallback_model,
                )
                llm_res = await modelops_service.generate(db, fallback_llm_req)
                logger.info("Successfully recovered using fallback model '%s'", req.fallback_model)
                return llm_res.content.strip()
            except Exception as fb_err:
                logger.warning(
                    "ModelOps fallback model '%s' also failed (%s), using grounded context synthesis fallback",
                    req.fallback_model,
                    fb_err,
                )

        # Factual grounded synthesis fallback without hallucinating
        if fact_markdown:
            return (
                "Dựa trên dữ liệu chính thức của Trường Đại học Quy Nhơn, mình xin gửi thông tin chi tiết đến bạn:\n\n"
                f"{fact_markdown}\n\n"
                f"**Thông tin bổ sung:**\n"
                f"{candidates[0].content[:400] if candidates else ''}"
            )
        if candidates:
            return (
                "Chào bạn! Dựa trên tài liệu chính thức của Trường Đại học Quy Nhơn, mình xin giải đáp như sau:\n\n"
                f"{candidates[0].content}"
            )
        return citation_guard.get_no_answer_response(req.module_code)


rag_service = RagService()
