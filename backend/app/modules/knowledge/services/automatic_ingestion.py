"""Versioned content readiness, independent of optional semantic approval/publication."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import AppException
from app.modules.knowledge.services.derived_bundle import digest, source_fingerprint
from app.modules.knowledge.services.smart_approval import collect_quality_findings

POLICY = "automatic-content-v1"
READY = {"AUTO_READY", "READY_WITH_LIMITATIONS"}


def evaluate_content(artifact: dict, quality: dict) -> dict:
    """A readable uninterpreted literal is not an extraction failure or a numeric fact."""
    findings = {"blockers": [], "warnings": []}
    collect_quality_findings(artifact, findings)
    limitations = []
    for table in artifact.get("tables", []):
        for row_id, fields in zip(table["row_unit_ids"], table["row_fields"], strict=True):
            for field in fields:
                if field["state"] not in {"ambiguous", "unreadable", "blank", "not_stated"}:
                    continue
                target = {"table_id": table["id"], "row_unit_id": row_id, "column_id": field["column_id"]}
                raw = field.get("raw")
                if field["state"] == "unreadable" or not isinstance(raw, str) or (field["state"] == "ambiguous" and not raw.strip()):
                    findings["blockers"].append({**target, "reason_code": "SOURCE_CELL_UNREADABLE", "message": "Có ô dữ liệu chưa đọc được từ nguồn."})
                    continue
                if any(f["raw_data"].get("source_unit_id") == row_id and f["raw_data"].get("column_id") == field["column_id"] for f in artifact.get("facts", [])):
                    findings["blockers"].append({**target, "reason_code": "UNKNOWN_USED_AS_FACT", "message": "Ô chưa xác định đang được dùng làm dữ kiện chắc chắn."})
                basis = {"blank": "source_blank", "not_stated": "source_not_stated"}.get(field["state"], "literal_uninterpreted")
                limitations.append({**target, "raw": raw, "state": field["state"], "basis": basis,
                    "usage": "description_only", "message": "Giữ nguyên ký hiệu; chưa đủ căn cứ diễn giải hoặc dùng trong phép tính."})
    if quality.get("overall_status") == "failed":
        findings["blockers"].append({"reason_code": "QUALITY_GATE_FAILED", "message": "Kiểm tra chất lượng nội dung chưa đạt."})
    for flag in quality.get("warning_flags", []):
        findings["blockers"].append({"reason_code": str(flag), "message": "Có dấu hiệu nội dung cần đối chiếu với tệp nguồn."})
    for issue in quality.get("issues", []):
        if issue.get("severity") in {"error", "critical", "blocking"}:
            findings["blockers"].append({"reason_code": issue.get("code", "QUALITY_GATE_FAILED"), "message": issue.get("message", "Nội dung chưa đạt kiểm tra chất lượng.")})
    status = "NEEDS_ATTENTION" if findings["blockers"] else "READY_WITH_LIMITATIONS" if limitations else "AUTO_READY"
    return {"policy_version": POLICY, "status": status, **findings, "limitations": limitations,
        "semantic_mode": "verified_only", "publication_granted": False,
        "message": "Tài liệu cần kiểm tra nội dung." if status == "NEEDS_ATTENTION" else
            "Sẵn sàng nạp vector; các ký hiệu chưa rõ được giữ nguyên và không dùng làm dữ kiện chắc chắn." if limitations else
            "Đã chuẩn hóa và kiểm tra nội dung. Sẵn sàng nạp vector."}


def _proof(revision: Any, artifact: dict) -> str:
    return digest({"source": source_fingerprint(revision, artifact), "tables": artifact["tables"],
        "issues": artifact.get("issues", []), "integrity": artifact.get("content_integrity"),
        "quality": revision.quality_report, "policy": POLICY})


def content_readiness(revision: Any) -> dict | None:
    """Read-only: stale certificates fail closed, never upgrade historical approvals."""
    provenance = revision.parse_provenance or {}
    marker = provenance.get("automatic_ingestion")
    if marker is None:
        return None
    artifact = provenance.get("structured_artifact") or {}
    try:
        expected = evaluate_content(artifact, revision.quality_report or {})
        if marker.get("proof") != _proof(revision, artifact) or marker.get("result") != expected:
            raise ValueError("CONTENT_READINESS_STALE")
    except (ValueError, TypeError, KeyError, AppException):
        return {"policy_version": POLICY, "status": "NEEDS_ATTENTION", "limitations": [], "warnings": [],
            "blockers": [{"reason_code": "CONTENT_READINESS_STALE", "message": "Nội dung hoặc cấu hình kiểm tra đã thay đổi; cần kiểm tra lại."}],
            "message": "Nội dung cần kiểm tra lại trước khi nạp vector.", "publication_granted": False}
    return expected


async def verify_content_source(revision: Any) -> None:
    """Repeat source/pair integrity before indexing or publication, without parsing."""
    from app.modules.knowledge.services.qnu_serving import storage_service, verify_revision_pair
    from app.modules.knowledge.services.semantic_store import verify_effective_projection

    document = await verify_revision_pair(revision)
    artifact = revision.parse_provenance["structured_artifact"]
    await verify_effective_projection(revision, artifact, document)
    raw = await storage_service.get(revision.snapshot_storage_path)
    if raw is None or hashlib.sha256(raw).hexdigest() != revision.origin_file_hash:
        raise AppException("Tệp nguồn không khớp phiên bản.", code="SOURCE_HASH_MISMATCH", status_code=409)
    if document.document_meta.get("source_format") == "pdf":
        import asyncio
        import json

        from app.modules.knowledge.parsers.pdf_fidelity import verify_pdf_source
        from app.modules.knowledge.services.source_figure_review import KEY, verify_figure_reviews

        try:
            reference = (revision.snapshot_metadata or {})["qnu_markdown"]["raw_evidence"]
            evidence = await storage_service.get(reference["path"])
            if evidence is None or hashlib.sha256(evidence).hexdigest() != reference["sha256"]:
                raise ValueError("PDF_RAW_EVIDENCE_MISMATCH")
            from app.modules.knowledge.services.source_extraction import _native_pdf_lock

            async with _native_pdf_lock:
                await asyncio.to_thread(verify_pdf_source, document, raw, json.loads(evidence))
                await asyncio.to_thread(verify_figure_reviews, document, raw,
                    (revision.snapshot_metadata or {}).get(KEY) or [], revision.binding_id)
        except (ValueError, KeyError, TypeError) as exc:
            raise AppException("Nội dung PDF không còn khớp bằng chứng nguồn.", code="SOURCE_LAYOUT_MISMATCH", status_code=409) from exc
    if document.document_meta.get("source_format") == "docx":
        import asyncio

        from app.modules.knowledge.parsers.docx_layout_fidelity import verify_native_layout

        try:
            await asyncio.to_thread(verify_native_layout, document, raw)
            from app.modules.knowledge.services.source_figure_review import (
                KEY,
                verify_figure_reviews,
            )

            await asyncio.to_thread(verify_figure_reviews, document, raw,
                (revision.snapshot_metadata or {}).get(KEY) or [], revision.binding_id)
        except ValueError as exc:
            raise AppException("Lưới ô nguồn hoặc giới hạn diễn giải không còn khớp.", code="SOURCE_LAYOUT_MISMATCH", status_code=409) from exc


async def seal_automatic_content(revision: Any) -> dict:
    """Only new native ingestion/reparse opts in; no retroactive shared-DB writes."""
    await verify_content_source(revision)
    artifact = revision.parse_provenance["structured_artifact"]
    result = evaluate_content(artifact, revision.quality_report or {})
    revision.quality_report = {**(revision.quality_report or {}),
        "overall_status": "passed" if result["status"] in READY else "warning",
        "structured_review_required": result["status"] == "NEEDS_ATTENTION"}
    # Preserve fatal status; the second evaluation must see the exact stored policy inputs.
    if any(b["reason_code"] == "QUALITY_GATE_FAILED" for b in result["blockers"]):
        revision.quality_report["overall_status"] = "failed"
    result = evaluate_content(artifact, revision.quality_report)
    revision.parse_provenance = {**revision.parse_provenance, "automatic_ingestion": {
        "policy_version": POLICY, "at": datetime.now(UTC).isoformat(), "result": result,
        "proof": _proof(revision, artifact), "authority": "machine_content_validation"}}
    return result
