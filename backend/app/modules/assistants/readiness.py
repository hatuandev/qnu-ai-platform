"""Publish Gate Engine for QNU AI Assistant readiness assessment.

Evaluates an assistant against 5 enterprise criteria before publication:
1. Knowledge Base Readiness (indexed & active documents)
2. ModelOps & Redundancy Readiness (primary & fallback models)
3. Tool Gateway Readiness (allowlist validation against tool registry)
4. Guardrails & Safety Defense (injection defense, PII masking, no-answer policy)
5. Continuous Quality Evaluation (Ragas TM-08 standard compliance)
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistants.knowledge_readiness import count_ready_sources
from app.modules.assistants.model_readiness import check_model_routes
from app.modules.assistants.models import AssistantModel
from app.modules.assistants.runtime import resolve_execution_mode
from app.modules.assistants.schemas import (
    AssistantLifecycleConfig,
    AssistantReadinessResponse,
    ReadinessCheckItem,
)
from app.modules.evaluation.models import EvaluationRun
from app.modules.knowledge.models import KnowledgeCollection
from app.modules.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class AssistantReadinessEngine:
    """Evaluates assistant completeness and gates production publishing."""

    async def evaluate_readiness(
        self,
        session: AsyncSession,
        assistant: AssistantModel,
    ) -> AssistantReadinessResponse:
        """Execute all 5 readiness criteria checks for the given assistant."""
        config_dict = assistant.config or {}
        config = AssistantLifecycleConfig.model_validate(config_dict)

        checks: list[ReadinessCheckItem] = []
        blockers: list[str] = []
        warnings: list[str] = []

        # 1. Knowledge Base Readiness Check
        k_check, k_blocker, k_warn = await self._check_knowledge(session, assistant.collection_id, assistant.tenant_id)
        checks.append(k_check)
        if k_blocker:
            blockers.append(k_blocker)
        if k_warn:
            warnings.append(k_warn)

        # 2. ModelOps & Redundancy Check
        m_check, m_blocker, m_warn = self._check_model_policy(config.model_policy)
        try:
            route_errors = await check_model_routes(session, config)
        except Exception as exc:
            logger.warning("model_readiness_failed error_type=%s", type(exc).__name__)
            route_errors = ["Không thể xác nhận cấu hình ModelOps."]
        if route_errors:
            m_check.status = "failed"
            m_check.score = 0
            m_check.message = " ".join(route_errors)
            m_check.details["route_errors"] = route_errors
            m_blocker = m_check.message
        checks.append(m_check)
        if m_blocker:
            blockers.append(m_blocker)
        if m_warn:
            warnings.append(m_warn)

        # 3. Tool Gateway Allowlist Check
        if resolve_execution_mode(config) == "rag":
            t_check = ReadinessCheckItem(category="tools", name="Chế độ RAG trực tiếp",
                status="passed", score=100, message="Tra cứu không thực thi công cụ hành động hoặc DAG.",
                details={"execution_mode": "rag", "action_tools_active": False})
            t_blocker = t_warn = None
        else:
            t_check, t_blocker, t_warn = self._check_tool_policy(config.tools)
        checks.append(t_check)
        if t_blocker:
            blockers.append(t_blocker)
        if t_warn:
            warnings.append(t_warn)

        # 4. Guardrails & Safety Check
        g_check, g_blocker, g_warn = self._check_guardrails(config.guardrails)
        checks.append(g_check)
        if g_blocker:
            blockers.append(g_blocker)
        if g_warn:
            warnings.append(g_warn)

        # 5. TM-08 Continuous Evaluation Check
        e_check, e_blocker, e_warn = await self._check_evaluation(session, assistant.code)
        checks.append(e_check)
        if e_blocker:
            blockers.append(e_blocker)
        if e_warn:
            warnings.append(e_warn)

        # Calculate aggregated overall score
        total_score = sum(c.score for c in checks)
        overall_score = round(total_score / len(checks)) if checks else 0
        is_ready = len(blockers) == 0 and overall_score >= 65

        return AssistantReadinessResponse(
            assistant_code=assistant.code,
            assistant_name=assistant.name,
            is_ready_for_publish=is_ready,
            overall_readiness_score=overall_score,
            checks=checks,
            blockers=blockers,
            warnings=warnings,
        )

    async def _check_knowledge(
        self, session: AsyncSession, collection_id: str | None,
        tenant_id: str | None = None,
    ) -> tuple[ReadinessCheckItem, str | None, str | None]:
        details = {"collection_id": collection_id, "ready_documents": 0}
        try:
            collection = await session.get(KnowledgeCollection, collection_id) if collection_id else None
            if not collection or (tenant_id and collection.tenant_id != tenant_id):
                raise ValueError("Kho tri thức chưa tồn tại hoặc không thuộc trợ lý.")
            count = await count_ready_sources(session, collection)
            details["ready_documents"] = count
            details["collection_epoch"] = collection.index_epoch
            if count:
                return (ReadinessCheckItem(
                    category="knowledge", name="Kho tri thức chuyên biệt", status="passed", score=100,
                    message=f"Kho tri thức có {count} nguồn đã xuất bản và sẵn sàng truy xuất.",
                    details=details), None, None)
            message = "Kho tri thức chưa có nguồn đã xuất bản đủ điều kiện truy xuất."
        except Exception as exc:
            logger.warning("failed_to_check_knowledge_readiness: %s", type(exc).__name__)
            message = "Không thể xác nhận Kho tri thức sẵn sàng. Kiểm tra nguồn đã xuất bản và phạm vi trợ lý."
        return (ReadinessCheckItem(
            category="knowledge", name="Kho tri thức chuyên biệt", status="failed", score=0,
            message=message, details=details), message, None)

    def _check_model_policy(
        self,
        policy: Any,
    ) -> tuple[ReadinessCheckItem, str | None, str | None]:
        """Verify primary and fallback models for operational resilience."""
        if isinstance(policy, dict):
            primary = policy.get("primary_model")
            fallback = policy.get("fallback_model")
            temperature = policy.get("temperature", 0.2)
        else:
            primary = getattr(policy, "primary_model", None)
            fallback = getattr(policy, "fallback_model", None)
            temperature = getattr(policy, "temperature", 0.2)

        if not primary:
            return (
                ReadinessCheckItem(
                    category="model",
                    name="ModelOps & Dự phòng chuyển đổi",
                    status="failed",
                    score=0,
                    message="Chưa cấu hình Primary Model.",
                    details={"primary_model": None, "fallback_model": fallback},
                ),
                "Thiếu Primary Model trong chính sách ModelOps.",
                None,
            )

        if not fallback:
            return (
                ReadinessCheckItem(
                    category="model",
                    name="ModelOps & Dự phòng chuyển đổi",
                    status="warning",
                    score=75,
                    message=f"Đã có Primary '{primary}' nhưng chưa cấu hình Fallback Model.",
                    details={"primary_model": primary, "fallback_model": None, "temperature": temperature},
                ),
                None,
                "Khuyến nghị cấu hình thêm Fallback Model để đảm bảo tính chịu lỗi khi Primary gặp sự cố.",
            )

        if primary == fallback:
            return (
                ReadinessCheckItem(
                    category="model",
                    name="ModelOps & Dự phòng chuyển đổi",
                    status="warning",
                    score=70,
                    message=f"Primary và Fallback cùng là '{primary}'. Khuyến nghị cấu hình 2 model độc lập để đảm bảo Circuit Breaker.",
                    details={"primary_model": primary, "fallback_model": fallback, "temperature": temperature},
                ),
                None,
                "Nên chọn Fallback Model từ nhà cung cấp khác để dự phòng khi Primary bị gián đoạn.",
            )

        return (
            ReadinessCheckItem(
                category="model",
                name="ModelOps & Dự phòng chuyển đổi",
                status="passed",
                score=100,
                message=f"Đã kích hoạt dự phòng 2 tầng: Primary ({primary}) ➔ Fallback ({fallback}), Temperature={temperature}.",
                details={"primary_model": primary, "fallback_model": fallback, "temperature": temperature},
            ),
            None,
            None,
        )

    def _check_tool_policy(
        self,
        policy: Any,
    ) -> tuple[ReadinessCheckItem, str | None, str | None]:
        """Validate all declared tools against system tool registry."""
        enabled_tools = getattr(policy, "enabled_tools", []) or []
        human_approval = getattr(policy, "human_approval_required", True)

        if not enabled_tools:
            return (
                ReadinessCheckItem(
                    category="tools",
                    name="Chốt chặn công cụ (Tool Gateway)",
                    status="passed",
                    score=95,
                    message="Chế độ RAG thông tin thuần túy (không phân quyền gọi công cụ bên ngoài).",
                    details={"enabled_tools": [], "human_approval": human_approval},
                ),
                None,
                None,
            )

        unregistered = [t for t in enabled_tools if tool_registry.get(t) is None]
        if unregistered:
            return (
                ReadinessCheckItem(
                    category="tools",
                    name="Chốt chặn công cụ (Tool Gateway)",
                    status="failed",
                    score=30,
                    message=f"Các công cụ sau chưa được đăng ký trong Tool Registry: {', '.join(unregistered)}.",
                    details={"enabled_tools": enabled_tools, "unregistered": unregistered},
                ),
                f"Công cụ chưa đăng ký trong Tool Registry: {', '.join(unregistered)}.",
                None,
            )

        warning = None
        if not human_approval:
            warning = "Các công cụ tự động kích hoạt mà chưa bật chế độ Human-in-the-loop (phê duyệt trước khi thực thi)."

        return (
            ReadinessCheckItem(
                category="tools",
                name="Chốt chặn công cụ (Tool Gateway)",
                status="passed",
                score=100 if human_approval else 85,
                message=f"{len(enabled_tools)} công cụ đã đăng ký hợp lệ ({', '.join(enabled_tools)}). Chế độ phê duyệt: {'Đã bật' if human_approval else 'Tự động'}.",
                details={"enabled_tools": enabled_tools, "human_approval": human_approval},
            ),
            None,
            warning,
        )

    def _check_guardrails(
        self,
        policy: Any,
    ) -> tuple[ReadinessCheckItem, str | None, str | None]:
        """Validate safety guardrails, prompt defense and no-answer policy."""
        block_injection = getattr(policy, "block_prompt_injection", True)
        mask_pii = getattr(policy, "mask_pii", True)
        no_answer = getattr(policy, "no_answer_message", "") or ""

        if not no_answer or len(no_answer.strip()) < 10:
            return (
                ReadinessCheckItem(
                    category="guardrails",
                    name="An toàn & Chống bịa đặt (Guardrails)",
                    status="failed",
                    score=20,
                    message="Chưa cấu hình Thông điệp cứu cánh No-Answer Policy khi không tìm thấy căn cứ văn bản.",
                    details={"block_injection": block_injection, "mask_pii": mask_pii},
                ),
                "Bắt buộc thiết lập thông điệp No-Answer Policy khi thiếu căn cứ RAG.",
                None,
            )

        has_contact = any(
            k in no_answer.lower()
            for k in ["hotline", "liên hệ", "0256", "phòng", "email", "trực tiếp", "@qnu.edu.vn", "sđt"]
        )

        score = 100
        warning = None
        if not has_contact:
            score -= 15
            warning = "Thông điệp No-Answer nên chứa đầu mối liên hệ (Hotline/Phòng ban) để điều hướng người dùng khi cần."
        if not block_injection:
            score -= 20
            warning = "Chưa bật chế độ chặn Prompt Injection / Jailbreak."
        if not mask_pii:
            score -= 15
            warning = "Chưa kích hoạt mặt nạ che giấu thông tin cá nhân (PII Masking)."

        return (
            ReadinessCheckItem(
                category="guardrails",
                name="An toàn & Chống bịa đặt (Guardrails)",
                status="passed" if score >= 80 else "warning",
                score=score,
                message=f"Hàng rào an toàn: Chặn Injection ({'Bật' if block_injection else 'Tắt'}), Che PII ({'Bật' if mask_pii else 'Tắt'}), No-Answer Policy ({'Có đầu mối' if has_contact else 'Chưa có đầu mối'}).",
                details={
                    "block_injection": block_injection,
                    "mask_pii": mask_pii,
                    "has_contact": has_contact,
                },
            ),
            None,
            warning,
        )

    async def _check_evaluation(
        self,
        session: AsyncSession,
        assistant_code: str,
    ) -> tuple[ReadinessCheckItem, str | None, str | None]:
        """Check if assistant has passed Ragas TM-08 academic quality benchmark."""
        try:
            stmt = (
                select(EvaluationRun)
                .where(EvaluationRun.assistant_code == assistant_code, EvaluationRun.status == "completed")
                .order_by(EvaluationRun.created_at.desc())
                .limit(1)
            )
            res = await session.execute(stmt)
            latest_run = res.scalar_one_or_none()

            if not latest_run:
                return (
                    ReadinessCheckItem(
                        category="evaluation",
                        name="Kiểm định chất lượng Ragas TM-08",
                        status="warning",
                        score=65,
                        message="Chưa có phiên chạy kiểm định benchmark Ragas TM-08 nào cho trợ lý này.",
                        details={"runs_found": 0},
                    ),
                    None,
                    "Khuyến nghị chạy kiểm định Benchmark Ragas TM-08 tại trang /evaluation trước khi xuất bản chính thức.",
                )

            eval_method = getattr(latest_run, "evaluation_method", "heuristic") or "heuristic"
            if latest_run.meets_tm08_standard:
                return (
                    ReadinessCheckItem(
                        category="evaluation",
                        name="Kiểm định chất lượng Ragas TM-08",
                        status="passed",
                        score=100,
                        message=f"Đạt chuẩn TM-08: Faithfulness {latest_run.faithfulness_avg:.2f} (>=0.90), Relevance {latest_run.answer_relevance_avg:.2f} (>=0.85), Pass rate {int(latest_run.pass_rate * 100)}% ({latest_run.passed_cases}/{latest_run.total_cases} câu, {eval_method}).",
                        details={
                            "run_id": latest_run.id,
                            "dataset_id": latest_run.dataset_id,
                            "faithfulness": latest_run.faithfulness_avg,
                            "relevance": latest_run.answer_relevance_avg,
                            "precision": latest_run.context_precision_avg,
                            "pass_rate": latest_run.pass_rate,
                            "passed_cases": latest_run.passed_cases,
                            "total_cases": latest_run.total_cases,
                            "evaluation_method": eval_method,
                        },
                    ),
                    None,
                    None,
                )

            return (
                ReadinessCheckItem(
                    category="evaluation",
                    name="Kiểm định chất lượng Ragas TM-08",
                    status="warning",
                    score=max(40, int(latest_run.pass_rate * 100)),
                    message=f"Phiên kiểm định gần nhất chưa đạt toàn bộ chuẩn TM-08: Faithfulness {latest_run.faithfulness_avg:.2f}, Relevance {latest_run.answer_relevance_avg:.2f}, Pass rate {int(latest_run.pass_rate * 100)}% ({latest_run.passed_cases}/{latest_run.total_cases} câu, {eval_method}).",
                    details={
                        "run_id": latest_run.id,
                        "dataset_id": latest_run.dataset_id,
                        "faithfulness": latest_run.faithfulness_avg,
                        "relevance": latest_run.answer_relevance_avg,
                        "precision": latest_run.context_precision_avg,
                        "pass_rate": latest_run.pass_rate,
                        "passed_cases": latest_run.passed_cases,
                        "total_cases": latest_run.total_cases,
                        "evaluation_method": eval_method,
                    },
                ),
                None,
                f"Kết quả kiểm định gần nhất chưa đạt chuẩn TM-08 (Đạt {int(latest_run.pass_rate * 100)}%).",
            )
        except Exception as exc:
            logger.warning("failed_to_check_evaluation_readiness: %s", exc)
            return (
                ReadinessCheckItem(
                    category="evaluation",
                    name="Kiểm định chất lượng Ragas TM-08",
                    status="warning",
                    score=60,
                    message="Không thể tải lịch sử kiểm định TM-08.",
                    details={"error": str(exc)},
                ),
                None,
                "Không thể kết nối dữ liệu kiểm định TM-08.",
            )


readiness_engine = AssistantReadinessEngine()
