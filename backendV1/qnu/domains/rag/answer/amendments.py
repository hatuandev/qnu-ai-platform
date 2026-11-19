"""Partial Amendments Resolution, Scope Facets & Non-tabular Block Formatters (Slice 6B).

Implements Pillar 1: Cross-document Partial Amendments & Lifecycle Governance
and Section 2.7: Generalized Metadata (scope_facets, lifecycle) and non-tabular
block types (procedure, form_template, visual_desc) from RULE_REASONING_PROMPTS_SPEC.md.
"""

from __future__ import annotations

import re
from typing import Any

_AMENDMENT_INQUIRY_PATTERNS = [
    r"\bsửa\s*đổi\b",
    r"\bbổ\s*sung\b",
    r"\bthay\s*thế\b",
    r"\bhết\s*hiệu\s*lực\b",
    r"\bcòn\s*hiệu\s*lực\b",
    r"\btrước\s*đây\b",
    r"\bquy\s*định\s*mới\b",
    r"\bquy\s*định\s*cũ\b",
    r"\báp\s*dụng\s*từ\b",
    r"\bđiều\s*chỉnh\b",
    r"\bso\s*với\s*quy\s*định\b",
    r"\bvăn\s*bản\s*mới\b",
    r"\bvăn\s*bản\s*cũ\b",
]


def detect_amendment_inquiry(query: str) -> bool:
    """Return True if user query is asking about amendments, history, or transitions."""
    normalized = query.lower()
    return any(re.search(pat, normalized, re.IGNORECASE) for pat in _AMENDMENT_INQUIRY_PATTERNS)


def match_scope_facets(source_facets: dict[str, Any] | None, requested_facets: dict[str, Any]) -> bool:
    """Check if source facets satisfy all requested facet criteria."""
    if not requested_facets:
        return True
    if not source_facets:
        return False

    for key, req_val in requested_facets.items():
        if key not in source_facets:
            return False
        curr_val = source_facets[key]
        if isinstance(req_val, str) and isinstance(curr_val, str):
            if req_val.strip().casefold() != curr_val.strip().casefold():
                return False
        elif req_val != curr_val:
            return False
    return True


def filter_by_scope_facets(sources: list[Any], requested_facets: dict[str, Any]) -> list[Any]:
    """Filter candidate sources matching requested scope facets (departments, audience, etc.)."""
    if not requested_facets:
        return sources

    filtered = []
    for s in sources:
        structure = getattr(s, "structure", None) or (s.get("structure") if isinstance(s, dict) else {})
        facets = structure.get("scope_facets") or structure.get("attributes") or {}
        if match_scope_facets(facets, requested_facets):
            filtered.append(s)
    return filtered


def resolve_amendments(
    sources: list[Any],
    is_amendment_inquiry: bool = False,
) -> tuple[list[Any], dict[str, Any]]:
    """Resolve partial amendment relationships across retrieved sources.

    When an amending block amends a superseded block:
    - If inquiry is historical/comparative: preserves both versions with explicit provenance tags.
    - If inquiry is standard lookup: prioritizes the active amending block, tagging superseded
      provisions with explicit warning so they are not cited as current law.
    """
    amendments_detected = []
    source_map: dict[str, Any] = {}
    superseded_to_amender: dict[str, Any] = {}

    for s in sources:
        evidence_id = getattr(s, "evidence_id", None) or (s.get("evidence_id") if isinstance(s, dict) else None)
        citation = getattr(s, "citation", None) or (s.get("citation") if isinstance(s, dict) else None)
        if evidence_id:
            source_map[evidence_id] = s
        if citation:
            source_map[citation] = s

    # First pass: map amends_ref and superseded_by_ref
    for s in sources:
        structure = getattr(s, "structure", None) or (s.get("structure") if isinstance(s, dict) else {})
        lifecycle = structure.get("lifecycle") or {}
        amends_ref = lifecycle.get("amends_ref")
        status = lifecycle.get("status", "active")
        superseded_by = lifecycle.get("superseded_by_ref")

        if amends_ref and amends_ref in source_map:
            target = source_map[amends_ref]
            target_id = getattr(target, "evidence_id", None) or target.get("evidence_id")
            superseded_to_amender[target_id] = s
            amendments_detected.append({
                "amender": getattr(s, "evidence_id", None) or s.get("evidence_id"),
                "target": target_id,
                "type": "amends_ref",
                "effective_from": lifecycle.get("effective_from"),
            })
        elif superseded_by and superseded_by in source_map:
            amender = source_map[superseded_by]
            amender_id = getattr(amender, "evidence_id", None) or amender.get("evidence_id")
            s_id = getattr(s, "evidence_id", None) or s.get("evidence_id")
            superseded_to_amender[s_id] = amender
            amendments_detected.append({
                "amender": amender_id,
                "target": s_id,
                "type": "superseded_by_ref",
                "effective_from": lifecycle.get("effective_from"),
            })
        elif status == "superseded":
            s_id = getattr(s, "evidence_id", None) or s.get("evidence_id")
            superseded_to_amender[s_id] = None
            amendments_detected.append({
                "amender": None,
                "target": s_id,
                "type": "superseded_standalone",
                "effective_from": lifecycle.get("effective_from"),
            })

    # Second pass: tag passages or annotate
    for s in sources:
        s_id = getattr(s, "evidence_id", None) or (s.get("evidence_id") if isinstance(s, dict) else None)
        structure = getattr(s, "structure", None) or (s.get("structure") if isinstance(s, dict) else {})
        lifecycle = structure.get("lifecycle") or {}
        status = lifecycle.get("status", "active")
        effective_from = lifecycle.get("effective_from") or "quy định mới"

        if s_id in superseded_to_amender:
            amender = superseded_to_amender[s_id]
            amender_id = None
            amender_date = None
            if amender:
                amender_id = getattr(amender, "evidence_id", None) or (
                    amender.get("evidence_id") if isinstance(amender, dict) else None
                )
                amender_struct = getattr(amender, "structure", None) or (
                    amender.get("structure") if isinstance(amender, dict) else {}
                )
                amender_date = (amender_struct.get("lifecycle") or {}).get("effective_from")

            amender_id = amender_id or "văn bản sửa đổi"
            effective_date = amender_date or lifecycle.get("effective_from") or "quy định mới"
            note = (
                f"[LƯU Ý HIỆU LỰC: Điều khoản này ĐÃ BỊ THAY THẾ/SỬA ĐỔI bởi {amender_id} từ ngày {effective_date}]"
                if not is_amendment_inquiry
                else f"[QUY ĐỊNH CŨ (Đã bị thay thế bởi {amender_id} từ ngày {effective_date})]"
            )
            _prefix_source_text(s, note)

        elif lifecycle.get("amends_ref"):
            amends_ref = lifecycle.get("amends_ref")
            note = f"[QUY ĐỊNH SỬA ĐỔI / HIỆN HÀNH (Sửa đổi cho {amends_ref} có hiệu lực từ {effective_from})]"
            _prefix_source_text(s, note)

    trace = {
        "amendments_detected": len(amendments_detected) > 0,
        "is_amendment_inquiry": is_amendment_inquiry,
        "pairs": amendments_detected,
    }
    return sources, trace


def _prefix_source_text(source: Any, note: str) -> None:
    """Prepend an amendment warning note to all passages or raw text of a source."""
    if isinstance(source, dict):
        passages = source.get("source_passages") or []
        for p in passages:
            if "text" in p and not p["text"].startswith("["):
                p["text"] = f"{note}\n{p['text']}"
    else:
        passages = getattr(source, "source_passages", [])
        for p in passages:
            if isinstance(p, dict) and "text" in p and not p["text"].startswith("["):
                p["text"] = f"{note}\n{p['text']}"


# =========================================================================
# Formatters for Non-Tabular Block Types (SPEC Section 2.7)
# =========================================================================

def format_procedure_block(
    step_range: str | None,
    steps: list[str],
    title: str | None = None,
) -> str:
    """Format a multi-step administrative procedure block with continuous numbering."""
    lines = []
    if title:
        lines.append(f"### QUY TRÌNH: {title}")
    if step_range:
        lines.append(f"*(Các bước: {step_range})*")
    for i, step in enumerate(steps, 1):
        lines.append(f"**Bước {i}:** {step}")
    return "\n".join(lines)


def format_form_template_block(
    form_name: str,
    form_code: str | None,
    attachment_ref: str | None,
    download_url: str | None = None,
) -> str:
    """Format an attachment/form template block, preserving file link instead of empty table cells."""
    lines = [f"### BIỂU MẪU: {form_name}"]
    if form_code:
        lines.append(f"- **Mã biểu mẫu:** `{form_code}`")
    if attachment_ref:
        lines.append(f"- **Tham chiếu đính kèm:** {attachment_ref}")
    if download_url:
        lines.append(f"- **Tải biểu mẫu gốc:** [Tải tại đây]({download_url})")
    return "\n".join(lines)


def format_visual_desc_block(
    diagram_title: str,
    description: str,
    mermaid_code: str | None = None,
    source_page: int | None = None,
) -> str:
    """Format a visual diagram/flowchart description with structured text or Mermaid."""
    lines = [f"### SƠ ĐỒ / LƯU ĐỒ: {diagram_title}"]
    if source_page is not None:
        lines.append(f"*(Trang nguồn: {source_page})*")
    lines.append(f"**Mô tả nội dung:** {description}")
    if mermaid_code:
        lines.append("```mermaid")
        lines.append(mermaid_code.strip())
        lines.append("```")
    return "\n".join(lines)
