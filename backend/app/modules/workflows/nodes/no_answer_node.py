"""No-Answer Output Node Handler — Dispatches Official QNU Hotline & Referral Fallback."""

from __future__ import annotations

import logging

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

DEFAULT_NO_ANSWER_MESSAGE = (
    "Chào bạn! Thông tin này hiện chưa có trong tài liệu chính thức của Trường Đại học Quy Nhơn "
    "mà mình được cung cấp.\n\n"
    "Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ:\n"
    "- Ban Tư vấn Tuyển sinh & Đào tạo QNU: **0256.3846.156**\n"
    "- Email: **tuyensinh@qnu.edu.vn**\n"
    "- Phòng Đào tạo: Phòng 108, Nhà A1, Trường ĐH Quy Nhơn."
)


class OutputNoAnswerNodeHandler(BaseNodeHandler):
    """Formats polite insufficient-context refusal and directs user to official university hotlines."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        config = node_spec.config or {}
        message = (
            config.get("message")
            or config.get("default_message")
            or DEFAULT_NO_ANSWER_MESSAGE
        )
        status = config.get("status", "insufficient_context")

        context.outputs["answer"] = message
        context.outputs["status"] = status
        context.outputs["citations"] = []

        logger.info(
            "OutputNoAnswer [%s]: dispatched no-answer policy fallback (status=%s)",
            node_spec.id,
            status,
        )

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "answer": message,
                "status": status,
                "citations": [],
            },
        )
