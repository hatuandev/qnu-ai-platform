"""RAG Service — Complete Query, Hybrid Retrieval, Fact Layer & Answer Composition Pipeline."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.guardrails import input_guardrail, output_guardrail
from app.core.redis import semantic_cache
from app.core.retrieval_policy import configured_policy
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.composer import (
    GROUNDING_INSTRUCTION,
    answer_format_planner,
    build_generic_system_instruction,
    extract_suggested_questions,
    sanitize_rag_answer,
)
from app.modules.rag.evidence_validation import citation_locations, location_pages
from app.modules.rag.facts import fact_layer
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.query_router import (
    QueryAnalysis,
    QueryIntent,
    query_classifier,
    scope_history_by_topic,
)
from app.modules.rag.retrieval_diagnostics import attach_diagnostics, pack_hybrid_context
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.row_answer import answer_from_rows
from app.modules.rag.schemas import (
    AskRequest,
    AskResponse,
    Citation,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.modules.rag.source_rows import load_row_anchors, merge_row_anchors
from app.modules.rag.temporal_answer import decide_table_answer, is_temporal_table_question

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
    lowered = answer.lower()
    return any(phrase in lowered for phrase in REFUSAL_PHRASES)


class RagService:
    """Service orchestrating Hybrid Retrieval, Fact verification and RAG response generation."""

    async def search(self, db: AsyncSession, req: SearchRequest) -> SearchResponse:
        start_time = time.perf_counter()
        rp = None
        policy = req.retrieval_policy
        if req.assistant_code:
            from sqlalchemy import select

            from app.modules.assistants.models import AssistantModel

            record = (await db.execute(select(AssistantModel).where(
                AssistantModel.code == req.assistant_code, AssistantModel.collection_id == req.collection_id,
                AssistantModel.is_active.is_(True)))).scalar_one_or_none()
            if record is None:
                raise AppException("Không tìm thấy trợ lý hoạt động trong kho này.", code="ASSISTANT_NOT_FOUND", status_code=404)
            knowledge = (record.config or {}).get("knowledge_policy") or {}
            policy = configured_policy(record.config or {})
            rp = knowledge.get("reranker_policy")
        if policy is not None and policy.profile == "legacy":
            policy = None
        if policy is not None:
            policy = configured_policy({"knowledge_policy": {"retrieval_policy": policy.model_dump()}})
        trace = {}

        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(
            db,
            req.collection_id,
            pinned_snapshot=req.retrieval_snapshot or getattr(req, "snapshot", None),
            tenant_id=req.tenant_id,
            workspace_id=req.workspace_id,
        )

        candidates = await hybrid_retriever.retrieve(
            db=db,
            collection_id=req.collection_id,
            query=req.query,
            top_k=req.top_k,
            rerank_top_k=req.rerank_top_k,
            tenant_id=req.tenant_id,
            workspace_id=req.workspace_id,
            snapshot=snapshot,
            **({"reranker_policy": rp} if rp is not None else {}),
            **({"retrieval_policy": policy} if policy is not None else {}),
            diagnostics=trace,
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
                binding_id=c.binding_id,
                index_revision_id=c.index_revision_id,
                document_revision=c.document_revision,
            )
            for idx, c in enumerate(candidates, start=1)
        ]

        exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return SearchResponse(
            query=req.query,
            collection_id=req.collection_id,
            total_found=len(items),
            items=items,
            retrieval_snapshot=snapshot,
            snapshot=snapshot,
            execution_time_ms=exec_ms,
            retrieval_diagnostics=trace,
        )

    async def ask(self, db: AsyncSession, req: AskRequest, *, candidate_snapshot: Any | None = None) -> AskResponse:
        from app.modules.modelops.services.inference_policy import rag_chat_scope
        from app.modules.rag.conversation_router import finish_routing

        async with rag_chat_scope():
            response = await self._ask_conversation(db, req, candidate_snapshot=candidate_snapshot)
        return finish_routing(req, response)

    async def _ask_conversation(self, db: AsyncSession, req: AskRequest, *, candidate_snapshot: Any | None = None) -> AskResponse:
        from app.modules.rag.conversation_router import route_turn

        started = time.perf_counter()
        req._retrieval_diagnostics = {}
        if not input_guardrail.check(req.original_question or req.question).is_safe:
            return await self._ask(db, req, candidate_snapshot=candidate_snapshot)
        effective, resolution, direct = await route_turn(db, req)
        from app.modules.rag.query_constraints import metric_attributes, requested_unit

        current_metrics = metric_attributes(req.original_question or req.question)
        effective._current_fact_constraints = {
            **({'metrics': current_metrics} if current_metrics else {}),
            **({'unit': requested_unit(req.original_question or req.question)}
               if requested_unit(req.original_question or req.question) else {})}
        if direct is not None:
            req._retrieval_diagnostics = {'branch': 'conversation', 'retrieval_executed': False}
            direct.latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return attach_diagnostics(req, direct)
        if resolution and resolution["mode"] == "clarify":
            return AskResponse(status="insufficient_context",
                answer="Bạn muốn tìm hiểu chủ đề hoặc ngành nào, trong năm hay kỳ nào?",
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                answer_decision={"version": "conversation-resolution-v1", "status": "clarify",
                                 "question_resolution": resolution})
        if resolution and resolution.get("mode") in ("explain", "reformat", "filter"):
            from app.modules.rag.conversation_acts import answer_dialogue_act

            handled = await answer_dialogue_act(db, effective, resolution,
                                                candidate_snapshot=candidate_snapshot)
            if handled is not None:
                handled.answer_decision = {**(handled.answer_decision or {}), "question_resolution": resolution}
                handled.latency_ms = round((time.perf_counter() - started) * 1000, 2)
                return attach_diagnostics(effective, handled)
            if resolution["mode"] in {"explain", "reformat"}:
                # History is not evidence. Re-resolve the antecedent against the
                # current publication, with presentation-only instructions.
                antecedent = resolution.get("antecedent_question", "").strip()
                prior_analysis = query_classifier.analyze(antecedent, module_code=effective.module_code)
                if antecedent and "subject_combinations" not in prior_analysis.fact_attributes:
                    styled = effective.model_copy(update={"question": antecedent, "original_question": antecedent, "history": [],
                        "system_prompt": (effective.system_prompt or "") +
                        "\nYÊU CẦU TRÌNH BÀY: Người dùng muốn lời giải thích ngắn, dễ hiểu hơn cho câu hỏi này. "
                        "Dùng đoạn ngắn hoặc gạch đầu dòng thay bảng dài. Giữ điều kiện, ngoại lệ và năm từ nguồn. "
                        "Không thêm dữ kiện, không hỏi lại chủ đề đã rõ; lịch sử chỉ giúp hiểu ý định, không là bằng chứng."})
                    result = await self._ask(db, styled, candidate_snapshot=candidate_snapshot, presentation_mode="brief")
                    result.answer_decision = {**(result.answer_decision or {}), "question_resolution": resolution,
                                              "presentation_revalidated": True}
                    result.latency_ms = round((time.perf_counter() - started) * 1000, 2)
                    return attach_diagnostics(styled, result)
            return AskResponse(status="insufficient_context",
                answer="Mình chưa xác định chắc phần bạn muốn giải thích, rút gọn hoặc lọc. Bạn nhắc lại chủ đề và phạm vi cần xem nhé.",
                answer_decision={"version": "conversation-resolution-v2", "status": "clarify",
                                 "reason": "ACT_REQUIRES_CLARIFICATION", "question_resolution": resolution})
        result = await self._ask(db, effective, candidate_snapshot=candidate_snapshot)
        if resolution:
            result.answer_decision = {**(result.answer_decision or {}), "question_resolution": resolution}
        result.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return attach_diagnostics(effective, result)

    async def _ask(self, db: AsyncSession, req: AskRequest, *, candidate_snapshot: Any | None = None,
                   presentation_mode: str | None = None) -> AskResponse:
        start_time = time.perf_counter()

        # 1. Input Guardrail safety check (Prompt Injection)
        guard_res = input_guardrail.check(req.original_question or req.question)
        if guard_res.is_safe and req.original_question:
            guard_res = input_guardrail.check(req.question)
        if not guard_res.is_safe:
            return AskResponse(
                status="insufficient_context",
                answer=f"Yêu cầu của bạn không thể xử lý: {guard_res.reason}",
                answer_format="paragraph",
                citations=[],
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        snapshot = candidate_snapshot or await hybrid_retriever.resolve_retrieval_snapshot(
            db,
            req.collection_id,
            pinned_snapshot=req.retrieval_snapshot or getattr(req, "snapshot", None),
            tenant_id=req.tenant_id,
            workspace_id=req.workspace_id,
        )
        snapshot_fingerprint = snapshot.cache_fingerprint()
        from app.modules.rag.evidence_pipeline import answer_with_evidence
        from app.modules.rag.evidence_runtime import resolve_evidence_request

        req, evidence_policy = await resolve_evidence_request(db, req)
        retrieval_policy = configured_policy(req.runtime_policy)
        req._retrieval_diagnostics.update(profile="configured" if retrieval_policy else "legacy")
        from app.modules.rag.score_conversion_chat import maybe_convert_score

        converted = await maybe_convert_score(db, req)
        if converted is not None:
            req._retrieval_diagnostics.update(branch="score_conversion", retrieval_executed=False)
            return converted
        logger.info("rag_execution_branch assistant=%s snapshot=%s branch=%s", req.assistant_code,
                    snapshot.snapshot_id, "evidence" if evidence_policy.enabled else "fact_hybrid")
        if evidence_policy.enabled:
            req._retrieval_diagnostics.update(branch="evidence", retrieval_executed=True)
            return await answer_with_evidence(db, req, snapshot, evidence_policy,
                                              candidate_mode=candidate_snapshot is not None)
        from app.modules.rag.combination_enumeration import enumerate_combinations

        analysis = query_classifier.analyze(req.question, module_code=req.module_code)
        if req._current_fact_constraints.get('metrics'):
            analysis.fact_attributes = req._current_fact_constraints['metrics']
        if req._current_fact_constraints.get('metric'):
            analysis.fact_attributes = [req._current_fact_constraints['metric']]
        enumeration = await enumerate_combinations(db, req, snapshot, analysis,
            candidate_mode=candidate_snapshot is not None)
        if enumeration is not None:
            req._retrieval_diagnostics.update(branch="enumeration", retrieval_executed=False,
                budget_note="Exhaustive enumeration is not truncated by context_top_k")
            return enumeration
        from app.modules.rag.source_identity_enumeration import enumerate_source_identities

        identities = await enumerate_source_identities(db, req, snapshot, candidate_mode=candidate_snapshot is not None)
        if identities is not None:
            return identities
        from app.modules.rag.glossary_expansion import resolve_glossary_queries

        glossary_queries, glossary_trace = await resolve_glossary_queries(
            db, req.collection_id, req.question,
            plan_years=[int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", req.question)])
        glossary_version = glossary_trace.get("settings_version", 0) if glossary_trace.get("enabled") else 0
        policy_version = req.policy_fingerprint() + ":weighted-expansion-v1:verified-answer-v5" + (
            f":glossary-v{glossary_version}" if glossary_version else ":glossary-off")

        # 2. Check Semantic Cache (history-aware; skipped for context-dependent shorts)
        history_list = req.history if isinstance(req.history, list) else []
        question_word_count = len(re.findall(r"\w+", req.question or ""))
        is_context_dependent = bool(history_list) and question_word_count < 8
        history_hash = semantic_cache.hash_history(history_list) if history_list else None
        temporal_query = bool(re.search(r"\b(?:19|20)\d{2}\b", req.question))
        typed_fact_query = is_temporal_table_question(req.question, req.module_code)
        if is_context_dependent or candidate_snapshot is not None or temporal_query or typed_fact_query:
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
                collection_epoch=snapshot.collection_epoch,
                snapshot_fingerprint=snapshot_fingerprint,
                policy_version=policy_version,
            )
        if cached:
            req._retrieval_diagnostics.update(branch="cache", retrieval_executed=False)
            logger.info("Semantic cache HIT for query='%s'", req.question[:30])
            cached["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            cached["answer"] = sanitize_rag_answer(cached.get("answer", ""))
            return AskResponse.model_validate(cached)

        # 3. Query Intent Analysis & Fact-First Routing (module-aware, reusable)
        lookup_limit = 1000 if typed_fact_query else 10 if analysis.intent == QueryIntent.EXACT_FACT else 5

        from app.modules.rag.source_fact_resolution import resolve_fact_scope, verify_fact_proof

        source_scope = (await resolve_fact_scope(db, snapshot, req.question,
                        candidate_mode=candidate_snapshot is not None)) if typed_fact_query else None
        if source_scope is not None:
            req._retrieval_diagnostics['fact_resolution'] = source_scope.trace
            # Catalog aliases are retrieval hints, never source identity proof.
            analysis.entity_codes = [code for code in source_scope.resolved_codes if code]
            analysis.target_entities = list(dict.fromkeys(row['name'] for row in source_scope.rows.values()))

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
            active_index_revision_ids=set(snapshot.binding_revisions.values()),
            requested_years=[int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", req.question)],
            **({'source_scope': source_scope} if source_scope is not None else {}),
        )
        decision = decide_table_answer(req.question, facts, module_code=req.module_code,
            requested_metric=req._current_fact_constraints.get('metric'),
            requested_unit=req._current_fact_constraints.get('unit'),
            requested_metrics=req._current_fact_constraints.get('metrics'),
            source_entity_codes=analysis.entity_codes if source_scope else None,
            source_entity_names=analysis.target_entities if source_scope else None)
        if source_scope is not None and decision is None:
            facts = []  # A code in narrative prose is not permission to attach adjacent numeric facts.
        if source_scope is not None:
            source_scope.trace.update(candidate_fact_count=len(facts),
                selected_fact_ids=(decision or {}).get('matched_fact_ids', []),
                answer_decision_reason=(decision or {}).get('reason'))
            if decision and not set(source_scope.candidates).issubset(source_scope.resolved_codes):
                decision.update(status='missing', reason='ENTITY_CODE_UNRESOLVED', facts=[], claim_bindings=[],
                    matched_fact_ids=[], answer='Chưa đối chiếu được đầy đủ mã được hỏi với định danh trong nguồn đã xuất bản.')
            if decision and not source_scope.candidates and source_scope.ambiguous_identity:
                decision.update(status='ambiguous', reason='ENTITY_SCOPE_AMBIGUOUS', facts=[], claim_bindings=[],
                    matched_fact_ids=[], answer='Tên được hỏi có nhiều định danh hoặc phạm vi nguồn. Cần xác định mã hoặc nguồn trước khi chọn dữ liệu.')
            if decision and decision.get('matched_fact_ids'):
                proof = await verify_fact_proof(db, req, snapshot, source_scope, decision,
                    limit=retrieval_policy.context_top_k if retrieval_policy else evidence_policy.context_limit,
                    max_chars=retrieval_policy.max_context_chars if retrieval_policy else evidence_policy.max_context_chars)
                if not proof:
                    decision.update(status='missing', reason='FACT_PROOF_BUDGET_EXCEEDED', facts=[],
                        claim_bindings=[], matched_fact_ids=[], answer='Nhóm bằng chứng đầy đủ vượt ngân sách đối soát của lượt hỏi.')
        if source_scope is None and decision and decision["status"] == "missing" and not decision.get("claim_bindings"):
            from app.modules.rag.snapshot_fact_evidence import load_snapshot_table_evidence

            table_evidence = await load_snapshot_table_evidence(db, snapshot)
            if table_evidence:
                fallback = decide_table_answer(req.question, table_evidence, module_code=req.module_code)
                if fallback and (fallback["status"] != "missing" or not decision.get("unscoped_fact_ids")):
                    decision = fallback
        if (decision and decision["status"] == "missing" and not decision.get("claim_bindings")
                and decision.get("reason") == "DATA_YEAR_UNVERIFIED"):
            # Unknown cell years may have exact applicability in the linked table
            # introduction. Use the existing independent selector/auditor; never
            # promote a filename or issue date into a data year.
            rows = await load_row_anchors(db, snapshot, req.question, candidate_mode=candidate_snapshot is not None)
            if rows:
                row_answer = await answer_from_rows(db, req, snapshot, rows)
                if row_answer is not None and (row_answer.status == "answered"
                        or (row_answer.answer_decision or {}).get("reason") == "SOURCE_VALUE_VARIANTS"):
                    row_answer.latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return row_answer
                if row_answer is not None:
                    decision["row_scope_check"] = row_answer.answer_decision
        if decision is not None:
            from app.modules.rag.prose_fallback import answer_from_prose, can_check_prose

            if source_scope is None and can_check_prose(decision):
                prose_answer = await answer_from_prose(db, req, snapshot, evidence_policy, decision["reason"],
                    candidate_mode=candidate_snapshot is not None)
                if prose_answer is not None:
                    return prose_answer
            matched = decision.pop("facts", [])
            if (not facts and not matched and decision.get("reason") == "NO_COMPATIBLE_FACT_EVIDENCE"):
                # A genuinely empty result keeps the configured contact policy,
                # without appending a second refusal/greeting to scope warnings.
                decision["answer"] = citation_guard.get_no_answer_response(req.module_code)
            citations = [Citation(source_id=f.get("binding_id") or str(f["id"]),
                                  title=f.get("source_title") or f["entity_name"] + " — " + f["attribute_name"],
                                  page_number=f["raw_data"].get("page_number"),
                                  quote=f.get('canonical_quote') or f"{f['entity_name']} · {f['raw_data'].get('header_path') or f['attribute_name']} = {f['attribute_value']}",
                                  canonical_hash=f.get('canonical_hash'), span_start=f.get('span_start'), span_end=f.get('span_end'),
                                  source_pages=location_pages(f["raw_data"].get("source_locations")) or sorted({p for p in (f["raw_data"].get("page_number"), f["raw_data"].get("header_page_number")) if isinstance(p, int)}),
                                  source_locations=citation_locations(f["raw_data"]),
                                  binding_id=f.get("binding_id"), index_revision_id=f.get("index_revision_id"),
                                  source_revision_id=f["raw_data"].get("source_revision_id")) for f in matched]
            decision["glossary_expansion"] = glossary_trace
            citations.extend(Citation(source_id=ref['binding_id'], title='Chú thích nguồn', quote=ref['quote'],
                binding_id=ref['binding_id'], index_revision_id=ref['index_revision_id'],
                source_revision_id=ref['source_revision_id'], canonical_hash=ref['canonical_hash'],
                span_start=ref['start'], span_end=ref['end'], page_number=ref.get('page_number'))
                for ref in decision.get('proof_context_references', []))
            return AskResponse(status="answered" if decision["status"] == "supported" else "insufficient_context",
                               answer=decision["answer"], answer_format="markdown_table" if matched else "paragraph",
                               answer_decision=decision, citations=citations,
                               facts_used=matched, contexts=[decision["answer"]] if matched else [],
                               retrieval_snapshot=snapshot, snapshot=snapshot,
                               latency_ms=round((time.perf_counter() - start_time) * 1000, 2))
        # An untyped policy question must not inherit arbitrary numeric rows.
        # Typed table decisions above retain their own coordinate/provenance gate.
        if not analysis.fact_attributes:
            facts = []
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
            glossary_queries=glossary_queries,
            reranker_policy=req.reranker_policy,
            snapshot=snapshot,
            **({"retrieval_policy": retrieval_policy} if retrieval_policy else {}),
            diagnostics=req._retrieval_diagnostics,
            **({"candidate_mode": True, "read_mode_override": "revisioned"} if candidate_snapshot is not None else {}),
        )
        req._retrieval_diagnostics.update(branch="fact_hybrid", retrieval_executed=True)

        # 5. No-Answer Policy if context is empty
        rows = await load_row_anchors(db, snapshot, req.question, candidate_mode=candidate_snapshot is not None)
        if rows and analysis.is_fact_first:
            row_answer = await answer_from_rows(db, req, snapshot, rows)
            if row_answer is not None and (row_answer.answer_decision or {}).get("reason") != "ROW_SELECTION_NOT_APPLICABLE":
                from app.modules.rag.prose_fallback import answer_from_prose, can_check_prose

                if can_check_prose(row_answer.answer_decision):
                    prose_answer = await answer_from_prose(db, req, snapshot, evidence_policy,
                        row_answer.answer_decision["reason"], candidate_mode=candidate_snapshot is not None)
                    if prose_answer is not None:
                        return prose_answer
                row_answer.latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return row_answer
        row_limit = retrieval_policy.context_top_k if retrieval_policy else int((req.reranker_policy or {}).get("top_k") or rerank_top_k)
        candidates = merge_row_anchors(candidates, rows, row_limit)
        if rows and not analysis.fact_attributes:
            # Same entity does not prove the requested metric. Untyped fee/quota
            # cells must not outrank the full source row as 'verified' numbers.
            facts, fact_markdown = [], ""
        if not candidates and not facts:
            from app.modules.rag.prose_fallback import answer_from_prose

            recovered = await answer_from_prose(db, req, snapshot, evidence_policy, "NO_HYBRID_CONTEXT",
                candidate_mode=candidate_snapshot is not None)
            if recovered is not None:
                return recovered
            no_answer_text = citation_guard.get_no_answer_response(req.module_code)
            return AskResponse(
                status="insufficient_context",
                answer=no_answer_text,
                answer_decision={"status": "missing", "reason": "NO_VERIFIED_CONTEXT"},
                answer_format="paragraph",
                citations=[],
                retrieval_snapshot=snapshot,
                snapshot=snapshot,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 4b. Parent-style neighbor expansion (prompt-only background, never cited)
        neighbor_context = await hybrid_retriever.expand_with_neighbors(
            db,
            candidates,
            req.collection_id,
            window=1,
            max_expansions=2,
            snapshot=snapshot,
        )

        # 6. Format Planning
        chosen_format = answer_format_planner.plan_format(
            req.question,
            context_has_table=bool(
                facts or any("table" in (c.content or "").lower() for c in candidates)
            ),
        )
        if presentation_mode == "brief":
            chosen_format = "bullet_list"

        # 7. Assemble Prompt & Generate Answer via ModelOps LLM Runtime
        context_texts = [c.content for c in candidates]
        for neighbors in (neighbor_context or {}).values():
            for n_text in neighbors:
                if n_text and n_text not in context_texts:
                    context_texts.append(n_text)

        if retrieval_policy:
            candidates, context_texts, packing = pack_hybrid_context(
                candidates, neighbor_context or {}, fact_markdown, retrieval_policy.max_context_chars)
            # Neighbors are already packed. Do not append dropped groups again in the composer.
            neighbor_context = {}
            req._retrieval_diagnostics.update(packing=packing)
            if packing["budget_exceeded"] or (not context_texts and not facts):
                return AskResponse(status="insufficient_context",
                    answer="Các đoạn chứng cứ không vừa ngân sách ngữ cảnh đã cấu hình; chưa thể trả lời an toàn.",
                    answer_decision={"reason": "CONTEXT_BUDGET_INSUFFICIENT"})
        req._retrieval_diagnostics.update(branch="fact_hybrid", retrieval_executed=True,
            context_count=len(context_texts), context_characters=sum(map(len, context_texts)),
            supplemental_context=True, facts_count=len(facts))

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
        if presentation_mode == "brief":
            user_content += ("\nYêu cầu hiện tại: giải thích lại NGẮN GỌN, DỄ HIỂU bằng gạch đầu dòng, không dùng bảng. "
                "Mỗi ý một câu ngắn; giữ điều kiện và ngoại lệ quan trọng từ bằng chứng. "
                "Không lặp lời chào, không hỏi lại chủ đề đã rõ, không thêm dữ kiện.")
        if rows:
            user_content += (
                "\nĐỐI SOÁT HÀNG VÀ NGỮ CẢNH NGUỒN:\n"
                "- Tên cột và đoạn giới thiệu xác định ý nghĩa số liệu; không đổi loại chỉ số chỉ vì cùng thực thể.\n"
                "- Đọc đủ các cột được hỏi, giữ dấu và ô trống theo chú giải.\n"
                "- Ghi chú liên kết chỉ là ngữ cảnh; chỉ áp dụng điều kiện khi văn bản xác nhận phạm vi phù hợp.\n"
                "- Không dùng năm ban hành hoặc tên tệp để tự xác nhận năm áp dụng của hàng.\n"
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

        facts_used_payload = [
            {"entity": f.entity_name, "attr": f.attribute_name, "val": f.attribute_value}
            for f in facts
        ]
        clean_answer, suggested_questions = extract_suggested_questions(
            final_answer, current_query=req.question
        )

        # Sanitize answer from broken table pipes or verbatim multi-major dumps
        clean_answer = sanitize_rag_answer(clean_answer, target_entity=target_entity_str)
        # Judge the visible answer, not suggestion text or citations merely retrieved.
        final_citations = citation_guard.filter_evidence_citations(citations, clean_answer)
        has_evidence = bool(final_citations or facts_used_payload)
        refusal_detected = is_refusal_answer(clean_answer, has_evidence)
        status = "answered" if clean_answer.strip() and has_evidence and not refusal_detected else "insufficient_context"
        logger.info("rag_answer_validation status=%s refusal=%s citations=%d facts=%d",
                    status, refusal_detected, len(final_citations), len(facts_used_payload))
        if not has_evidence and not refusal_detected:
            clean_answer = citation_guard.get_no_answer_response(req.module_code)
            suggested_questions = []

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
                from app.modules.rag.prose_fallback import answer_from_prose

                recovered = await answer_from_prose(db, req, snapshot, evidence_policy, "NUMERIC_GROUNDING_FAILED",
                    candidate_mode=candidate_snapshot is not None)
                if recovered is not None:
                    return recovered
                return AskResponse(status="insufficient_context",
                    answer="Mình tìm thấy tài liệu liên quan, nhưng chưa đối chiếu chắc chắn được các con số trong câu trả lời. Mình chưa thể chốt số liệu này.",
                    citations=[], facts_used=[], retrieval_snapshot=snapshot, snapshot=snapshot,
                    answer_decision={"reason": "NUMERIC_GROUNDING_FAILED", "unsupported_numbers": ungrounded_numbers},
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 2))

            from app.modules.rag.canonical_candidates import bind_candidates, canonical_citation
            from app.modules.rag.response_audit import audit_visible_answer

            bound_candidates = await bind_candidates(db, snapshot, candidates, candidate_mode=candidate_snapshot is not None)
            verdict = await audit_visible_answer(db, req, snapshot, clean_answer, [c for c, _ in bound_candidates])
            req._retrieval_diagnostics["visible_answer_audit"] = verdict
            if not verdict["accepted"]:
                from app.modules.rag.prose_fallback import answer_from_prose

                recovered = await answer_from_prose(db, req, snapshot, evidence_policy,
                    "VISIBLE_ANSWER_NOT_SUPPORTED", candidate_mode=candidate_snapshot is not None)
                if recovered is not None:
                    return recovered
                return AskResponse(status="insufficient_context",
                    answer="Mình tìm thấy tài liệu liên quan nhưng chưa xác minh đủ nội dung để trả lời chắc chắn câu hỏi này.",
                    retrieval_snapshot=snapshot, snapshot=snapshot,
                    answer_decision={"reason": "VISIBLE_ANSWER_NOT_SUPPORTED", "verification": verdict},
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 2))
            # Cite the exact excerpts the semantic reader accepted, not a separate
            # word-overlap heuristic (which may miss paraphrases or keep an extra).
            used_ids = set(verdict["candidate_ids"])
            final_citations = list({block.id: canonical_citation(block, candidate.document_id) for candidate, block in bound_candidates
                                    if candidate.chunk_id in used_ids}.values())

        exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
        resp = AskResponse(
            status=status,
            answer=clean_answer,
            answer_format=chosen_format,
            citations=final_citations,
            facts_used=facts_used_payload,
            suggested_questions=suggested_questions,
            retrieval_snapshot=snapshot,
            snapshot=snapshot,
            latency_ms=exec_ms,
            contexts=[c.content for c in candidates],
            answer_decision={"glossary_expansion": glossary_trace,
                             "verification": req._retrieval_diagnostics.get("visible_answer_audit")},
        )

        # 9. Save to Semantic Cache (Only cache valid answered queries with citations)
        if status == "answered" and final_citations and not is_context_dependent and candidate_snapshot is None:
            await semantic_cache.set(
                req.collection_id,
                req.question,
                resp.model_dump(),
                req.preferred_model_name or "default",
                tenant_id=req.tenant_id,
                workspace_id=req.workspace_id,
                history_hash=history_hash,
                collection_epoch=snapshot.collection_epoch,
                snapshot_fingerprint=snapshot_fingerprint,
                policy_version=policy_version,
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
        """ModelOps alone owns retries/failover; infrastructure errors must propagate."""
        llm_messages = [message.model_copy(update={"content": message.content + "\n\n" + GROUNDING_INSTRUCTION})
                        if message.role == "system" else message for message in llm_messages]
        llm_req = LLMGenerateRequest(
            messages=llm_messages, tenant_id=req.tenant_id, assistant_code=req.assistant_code,
            temperature=temperature, max_tokens=req.max_tokens, thinking_budget=req.thinking_budget,
            conversation_id=req.conversation_id, preferred_provider_id=req.preferred_provider_id,
            preferred_model_name=req.preferred_model_name, fallback_model_name=req.fallback_model,
            fallback_provider_id=req.fallback_provider_id,
        )
        try:
            llm_res = await modelops_service.generate(db, llm_req)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("ModelOps generation failed")
            raise AppException("Không thể sinh câu trả lời từ ModelOps.", code="LLM_GENERATION_FAILED", status_code=502) from exc
        if not llm_res.content.strip():
            raise AppException("Mô hình trả nội dung rỗng.", code="LLM_EMPTY_RESPONSE", status_code=502)
        return llm_res.content.strip()


rag_service = RagService()
