"""Evaluation Service executing automated Continuous Evaluation (TM-08 Standard)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.evaluation.dataset_seeder import QNU_BENCHMARK_DATASETS
from app.modules.evaluation.evaluator import LLMJudgeTM08Evaluator, get_evaluator, tm08_evaluator
from app.modules.evaluation.models import EvaluationResultItem, EvaluationRun, KnowledgeGapRecord
from app.modules.evaluation.schemas import (
    DatasetResponse,
    EvaluationResultItemResponse,
    EvaluationRunDetailResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    KnowledgeGapResolveRequest,
    KnowledgeGapResponse,
    TestCaseResponse,
)

logger = structlog.get_logger(__name__)


class EvaluationService:
    """Service orchestrating Ragas TM-08 evaluations and drift detection."""

    def __init__(self) -> None:
        self.evaluator = tm08_evaluator

    def list_datasets(self) -> list[DatasetResponse]:
        """List built-in academic benchmark datasets."""
        return [
            DatasetResponse(
                id=d["id"],
                name=d["name"],
                description=d["description"],
                assistant_code=d["assistant_code"],
                total_test_cases=len(d.get("test_cases", [])),
            )
            for d in QNU_BENCHMARK_DATASETS
        ]

    def get_dataset_test_cases(self, dataset_id: str) -> list[TestCaseResponse]:
        """Get list of benchmark test cases for a specific dataset."""
        dataset = next((d for d in QNU_BENCHMARK_DATASETS if d["id"] == dataset_id), None)
        if not dataset:
            raise NotFoundException(f"Tập dữ liệu kiểm định '{dataset_id}' không tồn tại")

        return [
            TestCaseResponse(
                id=tc["id"],
                dataset_id=dataset_id,
                question=tc["question"],
                ground_truth=tc["ground_truth"],
                expected_source=tc["expected_source"],
                keywords=tc.get("keywords", []),
            )
            for tc in dataset.get("test_cases", [])
        ]

    async def run_evaluation(
        self,
        session: AsyncSession,
        request: EvaluationRunRequest,
    ) -> EvaluationRunResponse:
        """Execute continuous evaluation benchmark on an AI Assistant."""
        dataset = next((d for d in QNU_BENCHMARK_DATASETS if d["id"] == request.dataset_id), None)
        if not dataset:
            raise NotFoundException(f"Tập dữ liệu kiểm định '{request.dataset_id}' không tồn tại")

        test_cases = dataset.get("test_cases", [])
        if request.sample_size:
            test_cases = test_cases[: request.sample_size]

        run_id = str(uuid.uuid4())
        eval_method = request.evaluation_method or "heuristic"
        evaluator = get_evaluator(eval_method)

        logger.info(
            "evaluation_run_started",
            run_id=run_id,
            assistant_code=request.assistant_code,
            method=eval_method,
            total_cases=len(test_cases),
        )

        item_scores: list[dict[str, Any]] = []
        item_records: list[EvaluationResultItem] = []
        passed_count = 0

        for tc in test_cases:
            query = tc["question"]
            ground_truth = tc["ground_truth"]

            actual_answer = ""
            actual_contexts: list[str] = []
            execution_path = "assistant_workflow"

            # Execute real Assistant or RAG retrieval
            try:
                from app.modules.assistants.schemas import AssistantChatRequest
                from app.modules.assistants.service import assistant_service

                chat_res = await assistant_service.chat(
                    session,
                    request.assistant_code,
                    AssistantChatRequest(message=query),
                )
                actual_answer = chat_res.answer
                actual_contexts = [
                    c.get("quote", "")
                    for c in chat_res.citations
                    if isinstance(c, dict) and c.get("quote")
                ]
                execution_path = "assistant_workflow"
            except Exception as chat_err:
                logger.debug("assistant_chat_eval_fallback", error=str(chat_err))
                try:
                    from app.modules.rag.schemas import AskRequest
                    from app.modules.rag.service import rag_service

                    rag_res = await rag_service.ask(
                        session,
                        AskRequest(question=query, collection_id=f"col_{request.assistant_code}"),
                    )
                    actual_answer = rag_res.answer
                    actual_contexts = [c.quote for c in rag_res.citations if c.quote]
                    execution_path = "rag_service_fallback"
                except Exception:
                    actual_answer = ""
                    actual_contexts = []
                    execution_path = "failed_no_response"

            actual_answer = actual_answer or ""
            actual_contexts = actual_contexts or []

            if isinstance(evaluator, LLMJudgeTM08Evaluator):
                eval_res = await evaluator.evaluate_item_async(
                    session=session,
                    query=query,
                    ground_truth=ground_truth,
                    answer=actual_answer,
                    contexts=actual_contexts,
                    keywords=tc.get("keywords"),
                )
            else:
                eval_res = evaluator.evaluate_item(
                    query=query,
                    ground_truth=ground_truth,
                    answer=actual_answer,
                    contexts=actual_contexts,
                    keywords=tc.get("keywords"),
                )

            item_scores.append(eval_res)
            if eval_res["passed"]:
                passed_count += 1

            item_record = EvaluationResultItem(
                id=str(uuid.uuid4()),
                run_id=run_id,
                test_case_id=str(tc.get("id", f"tc_{uuid.uuid4().hex[:8]}")),
                query=query,
                generated_answer=actual_answer,
                contexts=actual_contexts,
                faithfulness_score=eval_res["faithfulness"],
                answer_relevance_score=eval_res["answer_relevance"],
                context_precision_score=eval_res["context_precision"],
                is_hallucinated=eval_res["is_hallucinated"],
                is_refusal=eval_res.get("is_refusal", False),
                passed_all_criteria=eval_res["passed"],
                execution_path=execution_path,
                reasoning=eval_res.get("reasoning"),
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
            item_records.append(item_record)

        total_cases = len(test_cases)
        pass_rate = round(passed_count / max(total_cases, 1), 3)

        faith_avg = round(sum(s["faithfulness"] for s in item_scores) / max(total_cases, 1), 3)
        rel_avg = round(sum(s["answer_relevance"] for s in item_scores) / max(total_cases, 1), 3)
        prec_avg = round(sum(s["context_precision"] for s in item_scores) / max(total_cases, 1), 3)

        meets_tm08 = (
            faith_avg >= evaluator.FAITHFULNESS_THRESHOLD
            and rel_avg >= evaluator.ANSWER_RELEVANCE_THRESHOLD
            and prec_avg >= evaluator.CONTEXT_PRECISION_THRESHOLD
            and pass_rate >= 0.80
        )

        run_record = EvaluationRun(
            id=run_id,
            dataset_id=request.dataset_id,
            assistant_code=request.assistant_code,
            status="completed",
            total_cases=total_cases,
            passed_cases=passed_count,
            pass_rate=pass_rate,
            faithfulness_avg=faith_avg,
            answer_relevance_avg=rel_avg,
            context_precision_avg=prec_avg,
            meets_tm08_standard=meets_tm08,
            evaluation_method=eval_method,
            metadata_info={"item_count": total_cases, "evaluation_method": eval_method},
            created_at=datetime.now(UTC).replace(tzinfo=None),
            completed_at=datetime.now(UTC).replace(tzinfo=None),
        )

        try:
            session.add(run_record)
            for item in item_records:
                session.add(item)
            await session.commit()
        except Exception as db_exc:
            logger.warning("failed_to_save_evaluation_run_and_items", error=str(db_exc))
            await session.rollback()

        return EvaluationRunResponse(
            id=run_id,
            dataset_id=request.dataset_id,
            assistant_code=request.assistant_code,
            status="completed",
            total_cases=total_cases,
            passed_cases=passed_count,
            pass_rate=pass_rate,
            faithfulness_avg=faith_avg,
            answer_relevance_avg=rel_avg,
            context_precision_avg=prec_avg,
            meets_tm08_standard=meets_tm08,
            evaluation_method=eval_method,
            metadata_info={"sample_size": total_cases, "evaluation_method": eval_method},
            created_at=run_record.created_at,
            completed_at=run_record.completed_at,
        )

    async def list_runs(
        self,
        session: AsyncSession,
        assistant_code: str | None = None,
    ) -> list[EvaluationRunResponse]:
        """List historical evaluation runs from database."""
        stmt = select(EvaluationRun).order_by(EvaluationRun.created_at.desc())
        if assistant_code:
            stmt = stmt.where(EvaluationRun.assistant_code == assistant_code)

        result = await session.execute(stmt)
        runs = result.scalars().all()

        return [
            EvaluationRunResponse(
                id=r.id,
                dataset_id=r.dataset_id,
                assistant_code=r.assistant_code,
                status=r.status,
                total_cases=r.total_cases,
                passed_cases=r.passed_cases,
                pass_rate=r.pass_rate,
                faithfulness_avg=r.faithfulness_avg,
                answer_relevance_avg=r.answer_relevance_avg,
                context_precision_avg=r.context_precision_avg,
                meets_tm08_standard=r.meets_tm08_standard,
                evaluation_method=getattr(r, "evaluation_method", "heuristic") or "heuristic",
                metadata_info=r.metadata_info or {},
                created_at=r.created_at,
                completed_at=r.completed_at,
            )
            for r in runs
        ]

    async def get_run_detail(
        self,
        session: AsyncSession,
        run_id: str,
    ) -> EvaluationRunDetailResponse:
        """Get comprehensive evaluation run details including all question items."""
        run_stmt = select(EvaluationRun).where(EvaluationRun.id == run_id)
        run_res = await session.execute(run_stmt)
        run = run_res.scalar_one_or_none()
        if not run:
            raise NotFoundException(f"Không tìm thấy phiên kiểm định '{run_id}'")

        items_stmt = (
            select(EvaluationResultItem)
            .where(EvaluationResultItem.run_id == run_id)
            .order_by(EvaluationResultItem.created_at.asc())
        )
        items_res = await session.execute(items_stmt)
        items = items_res.scalars().all()

        return EvaluationRunDetailResponse(
            id=run.id,
            dataset_id=run.dataset_id,
            assistant_code=run.assistant_code,
            status=run.status,
            total_cases=run.total_cases,
            passed_cases=run.passed_cases,
            pass_rate=run.pass_rate,
            faithfulness_avg=run.faithfulness_avg,
            answer_relevance_avg=run.answer_relevance_avg,
            context_precision_avg=run.context_precision_avg,
            meets_tm08_standard=run.meets_tm08_standard,
            evaluation_method=getattr(run, "evaluation_method", "heuristic") or "heuristic",
            metadata_info=run.metadata_info or {},
            created_at=run.created_at or datetime.now(UTC).replace(tzinfo=None),
            completed_at=run.completed_at,
            items=[
                EvaluationResultItemResponse(
                    id=it.id,
                    test_case_id=it.test_case_id,
                    query=it.query,
                    generated_answer=it.generated_answer,
                    contexts=it.contexts or [],
                    faithfulness_score=it.faithfulness_score,
                    answer_relevance_score=it.answer_relevance_score,
                    context_precision_score=it.context_precision_score,
                    is_hallucinated=it.is_hallucinated,
                    is_refusal=getattr(it, "is_refusal", False),
                    passed_all_criteria=it.passed_all_criteria,
                    execution_path=getattr(it, "execution_path", "assistant_workflow"),
                    reasoning=it.reasoning,
                )
                for it in items
            ],
        )

    async def get_run_items(
        self,
        session: AsyncSession,
        run_id: str,
    ) -> list[EvaluationResultItemResponse]:
        """Get granular test items for an evaluation run."""
        stmt = (
            select(EvaluationResultItem)
            .where(EvaluationResultItem.run_id == run_id)
            .order_by(EvaluationResultItem.created_at.asc())
        )
        res = await session.execute(stmt)
        items = res.scalars().all()
        return [
            EvaluationResultItemResponse(
                id=it.id,
                test_case_id=it.test_case_id,
                query=it.query,
                generated_answer=it.generated_answer,
                contexts=it.contexts or [],
                faithfulness_score=it.faithfulness_score,
                answer_relevance_score=it.answer_relevance_score,
                context_precision_score=it.context_precision_score,
                is_hallucinated=it.is_hallucinated,
                is_refusal=getattr(it, "is_refusal", False),
                passed_all_criteria=it.passed_all_criteria,
                execution_path=getattr(it, "execution_path", "assistant_workflow"),
                reasoning=it.reasoning,
            )
            for it in items
        ]

    async def get_summary_metrics(self, session: AsyncSession | None = None) -> dict[str, Any]:
        """Get aggregated academic benchmark quality metrics (Ragas TM-08) computed from real execution runs."""
        if session is not None:
            try:
                from sqlalchemy import func

                stmt = select(
                    func.count(EvaluationRun.id),
                    func.avg(EvaluationRun.faithfulness_avg),
                    func.avg(EvaluationRun.answer_relevance_avg),
                    func.avg(EvaluationRun.context_precision_avg),
                ).where(EvaluationRun.status == "completed")
                result = await session.execute(stmt)
                row = result.one_or_none()
                if row and row[0] and row[0] > 0:
                    count, faith_avg, rel_avg, prec_avg = row
                    return {
                        "faithfulness": round(float(faith_avg or 0.0), 3),
                        "answer_relevance": round(float(rel_avg or 0.0), 3),
                        "context_precision": round(float(prec_avg or 0.0), 3),
                        "target_faithfulness": 0.90,
                        "target_relevance": 0.85,
                        "target_precision": 0.80,
                        "total_evaluations": count,
                    }
            except Exception as exc:
                logger.warning("failed_to_aggregate_evaluation_metrics", error=str(exc))

        return {
            "faithfulness": 0.0,
            "answer_relevance": 0.0,
            "context_precision": 0.0,
            "target_faithfulness": 0.90,
            "target_relevance": 0.85,
            "target_precision": 0.80,
            "total_evaluations": 0,
        }

    async def record_gap(
        self,
        session: AsyncSession,
        *,
        assistant_code: str,
        collection_id: str | None = None,
        question: str,
    ) -> KnowledgeGapRecord | None:
        """Record an unanswered user question triggering No-Answer Policy into gap inbox."""
        clean_q = question.strip()
        if not clean_q or len(clean_q) < 5:
            return None

        try:
            stmt = (
                select(KnowledgeGapRecord)
                .where(
                    KnowledgeGapRecord.assistant_code == assistant_code,
                    KnowledgeGapRecord.question == clean_q,
                    KnowledgeGapRecord.status == "pending",
                )
                .limit(1)
            )
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            now = datetime.now(UTC).replace(tzinfo=None)
            if existing:
                existing.frequency += 1
                existing.updated_at = now
                await session.commit()
                await session.refresh(existing)
                return existing

            new_gap = KnowledgeGapRecord(
                id=str(uuid.uuid4()),
                assistant_code=assistant_code,
                collection_id=collection_id,
                question=clean_q,
                frequency=1,
                status="pending",
                created_at=now,
                updated_at=now,
            )
            session.add(new_gap)
            await session.commit()
            await session.refresh(new_gap)
            logger.info("recorded_new_knowledge_gap", assistant=assistant_code, question=clean_q)
            return new_gap
        except Exception as exc:
            logger.warning("failed_to_record_knowledge_gap", error=str(exc))
            return None

    async def get_gap_inbox(
        self,
        session: AsyncSession | None = None,
        *,
        assistant_code: str | None = None,
        status: str = "pending",
    ) -> list[dict[str, Any]]:
        """Get unanswered knowledge gap questions triggering No-Answer Policy."""
        if session is not None:
            try:
                stmt = select(KnowledgeGapRecord)
                if status != "all":
                    stmt = stmt.where(KnowledgeGapRecord.status == status)
                if assistant_code:
                    stmt = stmt.where(KnowledgeGapRecord.assistant_code == assistant_code)
                stmt = stmt.order_by(KnowledgeGapRecord.frequency.desc(), KnowledgeGapRecord.updated_at.desc()).limit(50)
                result = await session.execute(stmt)
                records = result.scalars().all()
                if records:
                    return [
                        {
                            "id": r.id,
                            "question": r.question,
                            "assistant_code": r.assistant_code,
                            "assistant_name": r.assistant_code.replace("_", " ").title(),
                            "collection_id": r.collection_id or f"col_{r.assistant_code}",
                            "reason": "Kích hoạt No-Answer Policy do thiếu tài liệu trong kho tri thức.",
                            "frequency": r.frequency,
                            "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                            "status": r.status,
                            "resolution_notes": r.resolution_notes,
                            "resolved_by": r.resolved_by,
                        }
                        for r in records
                    ]
            except Exception as exc:
                logger.warning("failed_to_load_gap_records_from_db", error=str(exc))

            # Fallback to failed evaluation runs if no explicit gap records yet
            try:
                run_stmt = (
                    select(EvaluationRun)
                    .where(EvaluationRun.meets_tm08_standard.is_(False))
                    .order_by(EvaluationRun.created_at.desc())
                    .limit(10)
                )
                run_res = await session.execute(run_stmt)
                failed_runs = run_res.scalars().all()
                if failed_runs:
                    return [
                        {
                            "id": f"gap_{r.id[:8]}",
                            "question": f"Kiểm định bộ '{r.dataset_id}' chưa đạt chuẩn TM-08 (Đạt {int(r.pass_rate * 100)}%)",
                            "assistant_code": r.assistant_code,
                            "assistant_name": r.assistant_code.replace("_", " ").title(),
                            "collection_id": f"col_{r.assistant_code}",
                            "reason": f"Faithfulness: {r.faithfulness_avg:.2f}, Relevance: {r.answer_relevance_avg:.2f}. Cần bổ sung văn bản chính thức.",
                            "frequency": max(1, r.total_cases - r.passed_cases),
                            "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                            "status": "pending",
                        }
                        for r in failed_runs
                    ]
            except Exception as exc:
                logger.warning("failed_to_load_fallback_gaps", error=str(exc))

        return []

    async def resolve_gap(
        self,
        session: AsyncSession,
        gap_id: str,
        req: KnowledgeGapResolveRequest,
    ) -> KnowledgeGapResponse:
        """Mark a knowledge gap as resolved or dismissed with resolution notes."""
        stmt = select(KnowledgeGapRecord).where(KnowledgeGapRecord.id == gap_id)
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise NotFoundException(f"Không tìm thấy lỗ hổng tri thức với ID '{gap_id}'.")
        record.status = req.status
        record.resolution_notes = req.resolution_notes
        record.resolved_by = req.resolved_by
        record.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(record)
        return KnowledgeGapResponse.model_validate(record)


evaluation_service = EvaluationService()



