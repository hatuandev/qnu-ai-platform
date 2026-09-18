"""Artifact Export Node Handler — Renders Word (.docx) & PDF documents and registers artifacts."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.modules.tools.document_generator import export_document_package
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)


def _detect_template_code(text: str) -> str:
    """Detect appropriate document template based on user request or content."""
    lower = text.lower()
    if "quyết định" in lower or "quyet_dinh" in lower:
        return "quyet_dinh"
    if "thông báo" in lower or "thong_bao" in lower:
        return "thong_bao"
    if "tờ trình" in lower or "to_trinh" in lower:
        return "to_trinh"
    return "to_trinh"


def _extract_title(text: str) -> str:
    """Extract or formulate a concise title from the text."""
    # Look for 'Về việc...' pattern
    match = re.search(r"Về việc\s+([^\n\r.]+)", text, re.IGNORECASE)
    if match:
        return f"Về việc {match.group(1).strip()}"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        first_line = lines[0]
        # Strip markdown headers
        clean = re.sub(r"^[#*_\-\s]+", "", first_line)
        return clean[:100] if len(clean) > 5 else "Về việc triển khai nhiệm vụ công tác"
    return "Về việc triển khai nhiệm vụ công tác"


class ArtifactExportNodeHandler(BaseNodeHandler):
    """Executes document rendering to DOCX and PDF, saving files to artifact storage."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        config = node_spec.config or {}
        raw_format = config.get("format", "docx,pdf")
        if isinstance(raw_format, str):
            formats = [f.strip() for f in raw_format.split(",") if f.strip()]
        elif isinstance(raw_format, list):
            formats = raw_format
        else:
            formats = ["docx", "pdf"]

        # Ensure both docx and pdf are produced when requested
        if "both" in formats or not formats:
            formats = ["docx", "pdf"]

        # 1. Source content from upstream nodes
        content_text = (
            context.node_data.get("llm_content")
            or context.node_data.get("draft")
            or context.inputs.get("message")
            or "Kính đề nghị Ban Giám hiệu xem xét và phê duyệt."
        )

        template_code = config.get("template_code") or _detect_template_code(content_text)
        title = _extract_title(content_text)

        context_data: dict[str, Any] = {
            "trich_yeu": title,
            "noi_dung": content_text,
            "chuc_vu_nguoi_ky": "HIỆU TRƯỞNG",
            "ho_ten_nguoi_ky": "PGS.TS. Đỗ Ngọc Mỹ",
            "noi_nhan": "- Như kính gửi;\n- Các đơn vị liên quan;\n- Lưu: VT, ĐT.",
            "don_vi_ban_hanh": "TRƯỜNG ĐẠI HỌC QUY NHƠN",
        }

        if template_code == "quyet_dinh":
            context_data["so_hieu"] = ".../QĐ-ĐHQN"
        elif template_code == "thong_bao":
            context_data["so_hieu"] = ".../TB-ĐHQN"
        else:
            context_data["so_hieu"] = ".../TTr-ĐHQN"

        clean_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title[:30].strip())
        base_name = f"qnu_{template_code}_{clean_title}"

        try:
            artifacts = await export_document_package(
                template_code=template_code,
                context=context_data,
                formats=formats,
                base_name=base_name,
            )
        except Exception as exc:
            logger.warning("ArtifactExportNodeHandler export failed: %s", exc)
            artifacts = []

        # Propagate artifacts to context
        existing = context.node_data.get("artifacts", [])
        if isinstance(existing, list):
            context.node_data["artifacts"] = existing + artifacts
        else:
            context.node_data["artifacts"] = artifacts

        context.outputs["artifacts"] = context.node_data["artifacts"]

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "status": "exported",
                "template_code": template_code,
                "artifacts": artifacts,
            },
        )
