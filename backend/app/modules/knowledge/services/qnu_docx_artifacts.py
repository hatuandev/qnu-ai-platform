"""Shared artifact storage for DOCX and PDF QNU RAG Markdown v1.0.

The standard file and its JSON structured companion are content-addressed on the
snapshot path. Rendering and validation are deterministic; no model is called and
no value is guessed. Failures are recorded as metadata with ``status: failed``
instead of silently producing a partial standard file.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.core.storage import storage_service
from app.modules.knowledge.normalization.qnu_markdown import (
    QnuStructuredDocument,
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.services.source_extraction import SourceExtraction

logger = logging.getLogger(__name__)

QNU_MARKDOWN_RENDERER_VERSION = "qnu-docx-render/v1"
QNU_MARKDOWN_SUPERSEDED_REASON = "superseded_revision_content"
_MAX_REPORTED_ISSUES = 20
_MAX_ERROR_DETAIL = 300
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


def _issue_dicts(issues: list[Any]) -> list[dict[str, Any]]:
    return [
        {"code": issue.code, "detail": issue.detail[:_MAX_ERROR_DETAIL], "block_id": issue.block_id}
        for issue in issues[:_MAX_REPORTED_ISSUES]
    ]


def _artifact_header(document_id: str, revision_id: str, schema_version: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "renderer_version": QNU_MARKDOWN_RENDERER_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "document_id": document_id,
        "revision_id": revision_id,
    }


async def _render_and_save(
    document: QnuStructuredDocument,
    *,
    document_id: str,
    revision_id: str,
    snapshot_path: str,
    artifact: dict[str, Any],
) -> dict[str, Any]:
    """Render, validate and persist the two content-addressed files for one revision identity."""
    try:
        markdown = render_qnu_markdown(document, document_id=document_id, revision_id=revision_id)
        report = validate_qnu_markdown(markdown)
        artifact["validation"] = {
            "ok": report.ok,
            "block_count": report.block_count,
            "errors": _issue_dicts(report.errors),
            "warnings": _issue_dicts(report.warnings),
            "warning_count": len(report.warnings),
        }
        if not report.ok:
            artifact.update(status="failed", reason="validation_failed")
            logger.warning(
                "qnu_markdown_validation_failed source_revision=%s errors=%s",
                revision_id,
                [error.code for error in report.errors[:5]],
            )
            return artifact
        structured_text = (
            json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        )
        markdown_bytes = markdown.encode("utf-8")
        structured_bytes = structured_text.encode("utf-8")
        markdown_hash = hashlib.sha256(markdown_bytes).hexdigest()
        structured_hash = hashlib.sha256(structured_bytes).hexdigest()
        markdown_path = f"{snapshot_path}.{markdown_hash}.qnu-rag-v1.md"
        structured_path = f"{snapshot_path}.{structured_hash}.qnu-doc-v1.json"
        if not await storage_service.exists(markdown_path):
            await storage_service.save(markdown_path, markdown_bytes)
        if not await storage_service.exists(structured_path):
            await storage_service.save(structured_path, structured_bytes)
        artifact.update(
            status="ready",
            path=markdown_path,
            sha256=markdown_hash,
            structured_path=structured_path,
            structured_sha256=structured_hash,
            page_mapping=document.document_meta.get("page_mapping"),
            stats=document.stats,
        )
        return artifact
    except Exception as exc:
        logger.exception("qnu_markdown_build_failed source_revision=%s", revision_id)
        artifact.update(status="failed", reason="build_error", error=type(exc).__name__)
        artifact["detail"] = str(exc)[:_MAX_ERROR_DETAIL]
        return artifact


async def build_qnu_markdown_artifact(
    *,
    extraction: SourceExtraction,
    document_id: str,
    revision_id: str,
    title: str | None,
    snapshot_path: str,
) -> dict[str, Any]:
    """Build, validate and save the standard artifacts; never raises for content issues."""
    document = extraction.qnu_document
    artifact = _artifact_header(document_id, revision_id)
    if extraction.pdf_evidence is not None:
        artifact["renderer_version"] = "qnu-pdf-render/v1"
        try:
            payload = await asyncio.to_thread(_evidence_bytes, extraction.pdf_evidence)
            checksum = hashlib.sha256(payload).hexdigest()
            path = f"{snapshot_path}.{checksum}.pdf-evidence-v1.json"
            await storage_service.save(path, payload)
            artifact["raw_evidence"] = {"path": path, "sha256": checksum}
        except Exception as exc:
            artifact.update(status="failed", reason="pdf_evidence_save_failed", error=type(exc).__name__)
            return artifact
        if extraction.qnu_build_error:
            artifact.update(status="failed", reason="pdf_structure_build_failed", error=extraction.qnu_build_error)
            return artifact
    if document is None:
        artifact.update(status="unavailable", reason="docling_document_unavailable")
        artifact["engine_used"] = extraction.engine_used
        return artifact
    artifact["schema_version"] = document.schema_version
    document = document.model_copy(deep=True)
    if extraction.pdf_evidence is not None:
        document.document_meta["raw_evidence"] = artifact["raw_evidence"]
        artifact["content_status"] = document.document_meta.get("content_status", "unreviewed")
    if title and title.strip():
        document.title = title.strip()
    return await _render_and_save(
        document, document_id=document_id, revision_id=revision_id, snapshot_path=snapshot_path, artifact=artifact
    )


def _evidence_bytes(evidence: dict[str, Any]) -> bytes:
    return (json.dumps(evidence, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


async def rebuild_qnu_markdown_for_revision(
    source: dict[str, Any] | None,
    *,
    document_id: str,
    revision_id: str,
    snapshot_path: str,
) -> dict[str, Any]:
    """Re-render a shared parse artifact under this revision's own identity.

    Reuse is valid only because the artifact key pins source hash, parser profile and OCR
    config; the standard file embeds ids, so the bytes are regenerated, never relabelled.
    The stored checksum is verified on the bytes actually read before anything is parsed,
    rendered or written: an unverified companion is never turned into a ready artifact.
    """
    source = source or {}
    artifact = _artifact_header(document_id, revision_id, source.get("schema_version"))
    artifact["derived_from_revision_id"] = source.get("revision_id")
    if source.get("status") != "ready" or not source.get("structured_path"):
        artifact.update(status="unavailable", reason="shared_artifact_not_ready")
        return artifact
    expected = source.get("structured_sha256")
    if not isinstance(expected, str) or not expected.strip():
        artifact.update(status="unavailable", reason="structured_checksum_missing")
        return artifact
    if not _SHA256_HEX.fullmatch(expected):
        artifact.update(status="unavailable", reason="structured_checksum_invalid")
        return artifact
    content = await storage_service.get(source["structured_path"])
    if not content:
        artifact.update(status="unavailable", reason="structured_artifact_missing")
        return artifact
    actual = hashlib.sha256(content).hexdigest()
    if actual != expected:
        logger.warning(
            "qnu_markdown_structured_checksum_mismatch source_revision=%s expected=%s actual=%s",
            revision_id,
            expected,
            actual,
        )
        artifact.update(
            status="failed", reason="structured_checksum_mismatch", expected_sha256=expected, actual_sha256=actual
        )
        return artifact
    try:
        document = QnuStructuredDocument.model_validate_json(content)
    except Exception as exc:
        logger.exception("qnu_markdown_structured_reload_failed source_revision=%s", revision_id)
        artifact.update(status="failed", reason="structured_artifact_invalid", error=type(exc).__name__)
        return artifact
    if document.document_meta.get("builder_version", "").startswith("pdf-"):
        artifact["renderer_version"] = "qnu-pdf-render/v1"
        reference = document.document_meta.get("raw_evidence") or {}
        expected_raw = reference.get("sha256")
        raw = await storage_service.get(reference["path"]) if reference.get("path") else None
        if not isinstance(expected_raw, str) or not _SHA256_HEX.fullmatch(expected_raw) or raw is None or hashlib.sha256(raw).hexdigest() != expected_raw:
            artifact.update(status="failed", reason="pdf_evidence_integrity_failed")
            return artifact
        artifact["raw_evidence"] = reference
        artifact["content_status"] = document.document_meta.get("content_status", "unreviewed")
    return await _render_and_save(
        document, document_id=document_id, revision_id=revision_id, snapshot_path=snapshot_path, artifact=artifact
    )


def superseded_qnu_markdown_artifact(prior: dict[str, Any] | None, revision_id: str) -> dict[str, Any]:
    """Invalidate an inherited artifact: reference kept, another revision's file never served."""
    prior = prior or {}
    return {
        "schema_version": prior.get("schema_version"),
        "renderer_version": prior.get("renderer_version"),
        "document_id": prior.get("document_id"),
        "revision_id": revision_id,
        "status": "unavailable",
        "reason": QNU_MARKDOWN_SUPERSEDED_REASON,
        "superseded_revision_id": prior.get("revision_id"),
        "superseded_sha256": prior.get("sha256"),
        "note": (
            "Bản hiệu đính không còn dùng tệp QNU RAG Markdown của bản trước; "
            "cần dựng lại từ nội dung đã hiệu đính trước khi tải tệp chuẩn."
        ),
    }



async def load_qnu_markdown(artifact: dict[str, Any] | None) -> bytes | None:
    """Read the saved standard Markdown; returns None when the artifact is not ready."""
    if not artifact or artifact.get("status") != "ready":
        return None
    path = artifact.get("path")
    if not path:
        return None
    return await storage_service.get(path)


async def save_qnu_document(document: QnuStructuredDocument, *, document_id: str,
                            revision_id: str, snapshot_path: str) -> dict[str, Any]:
    """Persist an edited standard under new server-owned revision identity."""
    artifact = _artifact_header(document_id, revision_id, document.schema_version)
    raw = document.document_meta.get("raw_evidence")
    if raw:
        artifact["raw_evidence"] = raw
    return await _render_and_save(document, document_id=document_id, revision_id=revision_id,
                                  snapshot_path=snapshot_path, artifact=artifact)
