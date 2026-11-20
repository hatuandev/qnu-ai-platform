"""Read completed OCR evidence with full scope, immutable hashes and literal tables."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.models import CompilationInput
from qnu.domains.knowledge.index.artifact_cache import (
    get_canonical_json,
    set_canonical_json,
)
from qnu.domains.knowledge.public_api import resolve_revision_scope
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.ocr.review import service as text_service
from qnu.domains.ocr.review.models import TextVersion
from qnu.domains.ocr.service import processing_service
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore


async def load_documents(
    db: AsyncSession,
    blob: BlobStore,
    workspace_id: str,
    collection_id: str,
    run_ids: list[str],
    text_versions: dict[str, int] | None = None,
) -> list[dict]:
    """Caller authorizes workspace first; never choose the latest revision implicitly."""
    documents = []
    for run_id in sorted(run_ids):
        run = await db.scalar(
            select(OcrProcessingRun).where(
                OcrProcessingRun.id == run_id,
                OcrProcessingRun.workspace_id == workspace_id,
                OcrProcessingRun.collection_id == collection_id,
            )
        )
        if run is None:
            raise EntityNotFound("Không tìm thấy OCR trong kho đã chọn.", code="ocr_run_not_found")
        scope = await resolve_revision_scope(
            db,
            workspace_id,
            collection_id,
            run.source_id,
            run.revision_id,
        )
        snapshot = await processing_service.snapshot(db, blob, run)
        cached_canonical = get_canonical_json(run.id, snapshot["canonical_sha256"])
        if cached_canonical is not None:
            canonical = cached_canonical
            sha = snapshot["canonical_sha256"]
        else:
            sha, payload = await processing_service.read_document(db, blob, run)
            canonical = json.loads(payload)
            set_canonical_json(run.id, sha, canonical)
        if (
            canonical["identity"]["source_sha256"] != scope.sha256
            or canonical["identity"]["revision_id"] != scope.revision_id
            or sha != snapshot["canonical_sha256"]
        ):
            raise Conflict(
                "Bằng chứng OCR không khớp revision.", code="compilation_source_mismatch"
            )
        selected = (text_versions or {}).get(run_id, 0)
        metadata = {}
        if selected:
            checked = await text_service.read_review(db, blob, run, selected)
            canonical, _, row = await text_service.document(db, blob, run, selected)
            metadata = {
                "original_canonical_sha256": sha,
                "text_version": {
                    "id": row.id,
                    "version": row.version,
                    "canonical_sha256": checked.canonical_sha256,
                    "markdown_sha256": checked.markdown_sha256,
                },
            }
            sha = checked.canonical_sha256
        failures = canonical.get("image_ocr_failures") or []
        documents.append(
            {
                "ocr_run_id": run.id,
                "canonical_sha256": sha,
                "manifest_sha256": snapshot["manifest_sha256"],
                "identity": canonical["identity"],
                "pages": canonical["pages"],
                "evidence": canonical["evidence"],
                **metadata,
                **({"image_ocr_failures": failures} if failures else {}),
            }
        )
    return documents


async def load_bound_documents(
    db: AsyncSession,
    blob: BlobStore,
    workspace_id: str,
    collection_id: str,
    bindings: list[CompilationInput],
) -> list[dict]:
    versions = {}
    for binding in bindings:
        if (binding.workspace_id, binding.collection_id) != (workspace_id, collection_id):
            raise Conflict("Liên kết nguồn khác phạm vi.", code="compilation_source_mismatch")
        if binding.text_version_id:
            row = await db.scalar(
                select(TextVersion).where(
                    TextVersion.id == binding.text_version_id,
                    TextVersion.run_id == binding.ocr_run_id,
                    TextVersion.workspace_id == workspace_id,
                    TextVersion.collection_id == collection_id,
                )
            )
            if row is None or row.original_sha256 != binding.original_canonical_sha256:
                raise Conflict("Liên kết bản sửa đã thay đổi.", code="compilation_source_mismatch")
            versions[binding.ocr_run_id] = row.version
    documents = await load_documents(
        db, blob, workspace_id, collection_id, [b.ocr_run_id for b in bindings], versions
    )
    by_id = {d["ocr_run_id"]: d for d in documents}
    for b in bindings:
        doc = by_id[b.ocr_run_id]
        if (b.canonical_sha256, b.manifest_sha256, b.text_version_id) != (
            doc["canonical_sha256"],
            doc["manifest_sha256"],
            doc.get("text_version", {}).get("id"),
        ):
            raise Conflict("Liên kết nguồn đã thay đổi.", code="compilation_source_mismatch")
    return documents


def citation_index(documents: list[dict]) -> dict:
    index = {}
    for doc in documents:
        for evidence_id, locator in doc["evidence"].items():
            ref = f"{doc['ocr_run_id']}:{evidence_id}"
            index[ref] = {
                **doc["identity"],
                "evidence_id": evidence_id,
                **locator,
                "canonical_sha256": doc["canonical_sha256"],
                "manifest_sha256": doc["manifest_sha256"],
            }
            if "text_version" in doc:
                index[ref].update(
                    {
                        "original_artifact": locator.get("artifact"),
                        "artifact": "text_review_document",
                        "text_version": doc["text_version"],
                        "original_canonical_sha256": doc["original_canonical_sha256"],
                    }
                )
    return index


def literal_tables(documents: list[dict]) -> list[dict]:
    return [
        {
            "citation": f"{doc['ocr_run_id']}:{block['evidence_id']}",
            "page_number": page["page_number"],
            "table": block["table"],
        }
        for doc in documents
        for page in doc["pages"]
        for block in page["blocks"]
        if block.get("table") is not None
    ]
