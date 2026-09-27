"""Render validated administrative drafts to DOCX and PDF artifacts."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from app.core.exceptions import AppException
from app.modules.tools.document_generator import export_document_package
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)


def _detect_template_code(text: str) -> str:
    normalized = text.casefold()
    if "quyết định" in normalized or "quyet_dinh" in normalized:
        return "quyet_dinh"
    if "thông báo" in normalized or "thong_bao" in normalized:
        return "thong_bao"
    return "to_trinh"


def _extract_title(text: str) -> str:
    match = re.search(r"về việc\s+([^\n\r.]+)", text, re.IGNORECASE)
    if match:
        return f"Về việc {match.group(1).strip()}"
    for line in text.splitlines():
        title = re.sub(r"^[#*_\-\s]+", "", line).strip()
        if len(title) > 5:
            return title[:300]
    return "[BỔ SUNG TRÍCH YẾU]"


def _safe_file_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    clean = re.sub(r"[^\w-]+", "_", normalized, flags=re.UNICODE).strip("_")
    return clean[:60] or "du_thao"


def _normalize_formats(value: Any) -> list[str]:
    if isinstance(value, str):
        formats = [item.strip().lower() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        formats = [str(item).strip().lower() for item in value if str(item).strip()]
    else:
        formats = ["docx", "pdf"]
    if not formats or "both" in formats:
        return ["docx", "pdf"]
    return list(dict.fromkeys(formats))


class ArtifactExportNodeHandler(BaseNodeHandler):
    """Save requested formats from the validated, structured drafting output."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        port_inputs = context.node_inputs.get(node_spec.id, {})
        draft = port_inputs.get("draft") or context.node_data.get("draft")
        if isinstance(draft, dict) and isinstance(draft.get("context"), dict):
            template_code = str(draft.get("template_code") or "")
            document_context = draft["context"]
            title = str(draft.get("title") or "du_thao")
        else:
            content = (
                port_inputs.get("content")
                or context.node_data.get("llm_content")
                or (draft if isinstance(draft, str) else None)
                or context.inputs.get("message")
            )
            if isinstance(draft, dict):
                content = draft.get("content") or draft.get("body") or draft.get("text") or content
            if not isinstance(content, str) or not content.strip():
                raise AppException(
                    "Node xuất tệp không nhận được nội dung dự thảo.",
                    code="artifact_draft_not_validated",
                    status_code=422,
                    details={"node_id": node_spec.id},
                )
            config = node_spec.config or {}
            title = _extract_title(content)
            template_code = str(config.get("template_code") or _detect_template_code(content))
            document_context = {
                "is_draft": True,
                "trich_yeu": title,
                "noi_dung": content,
            }

        formats = _normalize_formats(
            port_inputs.get("formats")
            or context.node_data.get("artifact_formats")
            or (node_spec.config or {}).get("format")
            or context.inputs.get("format")
        )
        base_name = "_".join(
            (
                "qnu",
                template_code,
                _safe_file_slug(str(draft.get("title") or "du_thao")),
                str(context.execution_id or "")[:8],
            )
        )
        try:
            artifacts = await export_document_package(
                template_code=template_code,
                context=document_context,
                formats=formats,
                base_name=base_name,
            )
        except Exception as exc:
            logger.exception("Administrative draft export failed for node '%s'", node_spec.id)
            raise AppException(
                f"Không thể xuất tệp dự thảo: {exc}",
                code="artifact_export_failed",
                status_code=502,
                details={"node_id": node_spec.id, "template_code": template_code},
            ) from exc

        exported_formats = {str(artifact.get("type")) for artifact in artifacts}
        missing_formats = sorted(set(formats) - exported_formats)
        warnings = (
            ["PDF chưa tạo được; kiểm tra trạng thái và cấu hình Gotenberg."]
            if "pdf" in missing_formats
            else []
        )
        if not artifacts:
            raise AppException(
                "Không tạo được tệp nào. Kiểm tra mẫu DOCX, kho lưu trữ và Gotenberg.",
                code="artifact_export_empty",
                status_code=502,
                details={"requested_formats": formats},
            )

        context.node_data["artifacts"] = artifacts
        context.node_data["artifact_warnings"] = warnings
        context.outputs["artifacts"] = artifacts
        context.outputs["missing_fields"] = draft.get("missing_fields", [])
        if missing_formats:
            context.node_data["assistant_status"] = "draft_created_with_warnings"

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "status": "exported",
                "template_code": template_code,
                "artifacts": artifacts,
                "missing_formats": missing_formats,
                "warnings": warnings,
            },
        )
