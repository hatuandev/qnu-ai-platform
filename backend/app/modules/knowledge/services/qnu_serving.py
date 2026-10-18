"""Verified standard pair -> one canonical serving representation, before human review."""

from __future__ import annotations

import asyncio
import hashlib
import re
from copy import deepcopy
from typing import Any

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.knowledge.normalization.qnu_markdown import (
    QNU_MARKDOWN_SCHEMA,
    QnuBlock,
    QnuStructuredDocument,
    parse_qnu_markdown,
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.normalization.qnu_projection import VERSION, project_document


def _invalid(reason: str) -> AppException:
    return AppException("Gói QNU MD/JSON không khớp nguồn; cần tạo hoặc duyệt lại bản chuẩn.",
                        code="QNU_STANDARD_INVALID", status_code=409, details={"reason": reason})


def standard_reference(revision: Any) -> dict:
    return (revision.snapshot_metadata or {}).get("qnu_markdown") or (revision.parse_provenance or {}).get("qnu_markdown") or {}


async def load_document(reference: dict, *, binding_id: str, revision_id: str,
                        origin_hash: str, snapshot_path: str) -> QnuStructuredDocument:
    """Verify both saved files, identities, source bytes identity and deterministic pair parity."""
    if (reference.get("status") != "ready" or reference.get("document_id") != binding_id
            or reference.get("revision_id") != revision_id or reference.get("schema_version") != QNU_MARKDOWN_SCHEMA):
        raise _invalid("identity_or_status")
    payloads = []
    for path_key, hash_key, suffix in [("path", "sha256", ".qnu-rag-v1.md"),
                                      ("structured_path", "structured_sha256", ".qnu-doc-v1.json")]:
        path, expected = reference.get(path_key), reference.get(hash_key)
        if (not isinstance(path, str) or not path.startswith(snapshot_path + ".") or not path.endswith(suffix)
                or ".." in path or "\\" in path):
            raise _invalid("artifact_path")
        data = await storage_service.get(path)
        if data is None or hashlib.sha256(data).hexdigest() != expected:
            raise _invalid("artifact_checksum")
        payloads.append(data)
    try:
        document = await asyncio.to_thread(QnuStructuredDocument.model_validate_json, payloads[1])
        expected_md = await asyncio.to_thread(render_qnu_markdown, document,
                                             document_id=binding_id, revision_id=revision_id)
        actual_md = payloads[0].decode("utf-8")
        report = await asyncio.to_thread(validate_qnu_markdown, actual_md)
        actual = await asyncio.to_thread(parse_qnu_markdown, actual_md)
        expected = await asyncio.to_thread(parse_qnu_markdown, expected_md)
    except (ValueError, TypeError) as exc:
        raise _invalid("artifact_shape") from exc
    # JSON object order is immaterial, while block order/content/metadata are not.
    same_blocks = [(block.metadata, block.body) for block in actual.blocks] == [(block.metadata, block.body) for block in expected.blocks]
    if (not report.ok or actual.frontmatter != expected.frontmatter or not same_blocks
            or document.source.sha256 != origin_hash or document.schema_version != QNU_MARKDOWN_SCHEMA):
        raise _invalid("pair_or_source_mismatch")
    raw = document.document_meta.get("raw_evidence")
    if raw:
        path = raw.get("path")
        if not isinstance(path, str) or not path.startswith(snapshot_path + ".") or ".." in path or "\\" in path:
            raise _invalid("raw_evidence_path")
        data = await storage_service.get(path)
        if data is None or hashlib.sha256(data).hexdigest() != raw.get("sha256"):
            raise _invalid("raw_evidence_checksum")
    return document


def input_reference(reference: dict) -> dict:
    return {key: reference.get(key) for key in ("schema_version", "document_id", "revision_id", "sha256", "structured_sha256")}


def serving_pages(revision: Any) -> tuple[list[dict], str]:
    """Studio projection by evidenced unit page, never put all unpaged text on page one."""
    from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
    from app.modules.knowledge.services.source_artifact import get_source_artifact

    manifest = resolve_unit_manifest(revision.canonical_markdown, get_source_artifact(revision))
    grouped: dict[int, list[str]] = {}
    unmapped = []
    for unit in manifest.units:
        if unit.is_container:
            continue
        if unit.page_number is None:
            unmapped.append(unit.text)
        else:
            grouped.setdefault(unit.page_number, []).append(unit.text)
    return ([{"page_number": page, "markdown_content": "\n\n".join(texts)} for page, texts in sorted(grouped.items())],
            "\n\n".join(unmapped))


def validate_projection_binding(revision: Any, artifact: dict | None) -> None:
    reference = standard_reference(revision)
    canonical_hash = hashlib.sha256((revision.canonical_markdown or "").encode()).hexdigest()
    stored = (artifact or {}).get("qnu_input", {})
    if (not artifact or artifact.get("input_format") != VERSION or reference.get("status") != "ready"
            or reference.get("schema_version") != QNU_MARKDOWN_SCHEMA
            or any(not isinstance(reference.get(key), str) or not re.fullmatch(r"[a-f0-9]{64}", reference[key])
                   for key in ("sha256", "structured_sha256"))
            or reference.get("document_id") != revision.binding_id or reference.get("revision_id") != revision.id
            or any(stored.get(key) != value for key, value in input_reference(reference).items())
            or canonical_hash != revision.canonical_hash or canonical_hash != artifact.get("content_hash")
            or canonical_hash != stored.get("projection_hash")):
        raise _invalid("serving_projection_binding")


async def verify_revision_pair(revision: Any) -> QnuStructuredDocument:
    reference = standard_reference(revision)
    return await load_document(reference, binding_id=revision.binding_id, revision_id=revision.id,
                               origin_hash=revision.origin_file_hash, snapshot_path=revision.snapshot_storage_path)


async def verify_approval_pair(revision: Any, decision: str) -> None:
    if decision == "approved" and (revision.parse_provenance or {}).get("standard_required"):
        await verify_revision_pair(revision)


async def prepare_standard_revision(revision: Any) -> None:
    """Opt new/reparsed supported sources into the standard, never mutate a published revision."""
    reference = standard_reference(revision)
    revision.parse_provenance = {**(revision.parse_provenance or {}), "standard_required": True}
    if reference.get("status") != "ready":
        artifact = deepcopy((revision.parse_provenance or {}).get("structured_artifact") or {})
        artifact["issues"] = [*(artifact.get("issues") or []), {"code": "QNU_STANDARD_UNAVAILABLE"}]
        artifact["review"] = {"status": "required"}
        revision.parse_provenance = {**revision.parse_provenance, "structured_artifact": artifact}
    else:
        document = await verify_revision_pair(revision)
        try:
            canonical, artifact = await asyncio.to_thread(project_document, document, input_reference(reference),
                                                         revision.citation_metadata or {})
        except (ValueError, TypeError, KeyError) as exc:
            raise _invalid("standard_projection_invalid") from exc
        if not canonical.strip():
            raise _invalid("empty_projection")
        from app.modules.knowledge.services.unit_annotation import enrich_source_units

        await enrich_source_units(canonical, artifact, getattr(revision, "tenant_id", "tenant_qnu"),
                                  (revision.snapshot_metadata or {}).get("unit_temporal_annotation"))
        revision.canonical_markdown = canonical
        revision.canonical_hash = hashlib.sha256(canonical.encode()).hexdigest()
        revision.parse_provenance = {**revision.parse_provenance, "canonical_format": VERSION,
                                     "structured_artifact": artifact}
    overall = "failed" if (revision.quality_report or {}).get("overall_status") == "failed" else "warning"
    revision.quality_report = {**(revision.quality_report or {}), "overall_status": overall,
                               "structured_review_required": True, "serving_format": VERSION}


def _restore_unchanged(original: Any, displayed: Any, edited: Any) -> Any:
    """Round-trip renderer escapes losslessly, changing only fields actually edited."""
    if edited == displayed:
        return deepcopy(original)
    if isinstance(edited, dict) and isinstance(original, dict) and isinstance(displayed, dict):
        return {key: _restore_unchanged(original[key], displayed[key], value)
                if key in original and key in displayed else value for key, value in edited.items()}
    if isinstance(edited, list) and isinstance(original, list) and isinstance(displayed, list) and len(edited) == len(original) == len(displayed):
        return [_restore_unchanged(old, shown, new) for old, shown, new in zip(original, displayed, edited, strict=True)]
    return edited


def document_from_edit(markdown: str, base: QnuStructuredDocument, *, binding_id: str, revision_id: str) -> QnuStructuredDocument:
    """Client edits content, never source identity, locations, machine raw data or approval."""
    report = validate_qnu_markdown(markdown)
    if not report.ok:
        raise _invalid("edited_standard_validation")
    parsed = parse_qnu_markdown(markdown)
    front = parsed.frontmatter or {}
    rendered_base = parse_qnu_markdown(render_qnu_markdown(base, document_id=binding_id, revision_id=revision_id))
    if (front.get("document_id") != binding_id or front.get("revision_id") != revision_id
            or front.get("source") != rendered_base.frontmatter.get("source")):
        raise _invalid("edited_source_identity")
    originals = {block.id: block for block in base.blocks}
    original_display = {block.metadata["id"]: block for block in rendered_base.blocks}
    if {block.metadata["id"] for block in parsed.blocks} != set(originals):
        raise _invalid("edited_block_identity")
    result = base.model_copy(deep=True)
    result.blocks = []
    for parsed_block in parsed.blocks:
        meta = parsed_block.metadata
        old = originals[meta["id"]]
        for key in ("field_sources", "source_ref", "engine_used"):
            if meta.get("attributes", {}).get(key) != original_display[old.id].metadata.get("attributes", {}).get(key):
                raise _invalid("edited_machine_provenance")
        if (meta["type"] != old.type or meta.get("parent_id") != old.parent_id
                or meta["source_locations"] != original_display[old.id].metadata["source_locations"]):
            raise _invalid("edited_source_location")
        edited = QnuBlock(id=old.id, parent_id=old.parent_id, type=old.type,
            source_locations=old.source_locations,
            source_label=_restore_unchanged(old.source_label, original_display[old.id].metadata.get("source_label"), meta.get("source_label")),
            section_path=_restore_unchanged(old.section_path, original_display[old.id].metadata["section_path"], meta["section_path"]),
            context_refs=meta.get("context_refs", []),
            attributes=_restore_unchanged(old.attributes, original_display[old.id].metadata["attributes"], meta["attributes"]),
            quality_flags=meta.get("quality_flags", []),
            body=parsed_block.body, source_data=old.source_data)
        if parsed_block.body == original_display[old.id].body:
            edited.body = old.body
        if old.type == "table_row" and edited.body != old.body and edited.attributes.get("fields") == old.attributes.get("fields"):
            raise _invalid("edit_record_fields_not_display_body")
        result.blocks.append(edited)
    edited_by_id = {block.id: block for block in result.blocks}
    for block in result.blocks:
        if block.type == "table_row":
            columns = edited_by_id[block.parent_id].attributes["columns"]
            fields = block.attributes["fields"]
            block.body = "\n\n".join(f"**{' / '.join(column['header_path']) or column['id']}:** "
                + (fields[column["id"]]["raw"] or "[Ô trống trong nguồn]") for column in columns)
    result.stats = {"content_edited": True, "block_count": len(result.blocks)}
    # Metadata including review_status is not a server approval or temporal verification.
    return result
