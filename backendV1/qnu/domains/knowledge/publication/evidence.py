"""Revalidate Compiler bytes and every source before approval/publication/serving."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.artifacts import json_bytes, read
from qnu.domains.knowledge.compilation.evidence import (
    citation_index,
    literal_tables,
    load_bound_documents,
)
from qnu.domains.knowledge.compilation.models import CompilationInput, CompilationRun
from qnu.domains.knowledge.models import KBSource
from qnu.domains.knowledge.public_api import read_revision_bytes, resolve_revision_scope
from qnu.domains.knowledge.publication.models import CompiledVersion
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore


@dataclass(frozen=True, slots=True)
class VersionBundle:
    input_sha256: str
    draft_sha256: str
    markdown_sha256: str
    bundle_sha256: str
    provenance: dict
    content: dict
    markdown: bytes
    documents: list[dict]


def digest(value: object) -> str:
    return hashlib.sha256(json_bytes(value)).hexdigest()


async def load_bundle(
    db: AsyncSession,
    blob: BlobStore,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    *,
    require_current: bool = False,
    allow_staged: bool = False,
    serving: bool = False,
) -> VersionBundle:
    """Trusted caller must resolve workspace/collection access before this lookup."""
    run = await db.scalar(
        select(CompilationRun).where(
            CompilationRun.id == run_id,
            CompilationRun.workspace_id == workspace_id,
            CompilationRun.collection_id == collection_id,
        )
    )
    if run is None:
        raise EntityNotFound(
            "Không tìm thấy bản biên soạn trong kho.", code="compilation_not_found"
        )
    if run.status != "completed":
        raise Conflict("Compiler chưa hoàn tất.", code="compilation_not_completed")
    bindings = list(
        (
            await db.scalars(
                select(CompilationInput).where(
                    CompilationInput.run_id == run.id,
                )
            )
        ).all()
    )
    documents = await load_bound_documents(db, blob, workspace_id, collection_id, bindings)
    if not documents:
        raise Conflict("Bản biên soạn thiếu nguồn.", code="publication_evidence_missing")
    for doc in documents:
        identity = doc["identity"]
        scope = await resolve_revision_scope(
            db, workspace_id, collection_id, identity["source_id"], identity["revision_id"]
        )
        await read_revision_bytes(blob, scope)
    source_rows = {d["ocr_run_id"]: d for d in documents}
    if any(
        (b.canonical_sha256, b.manifest_sha256)
        != (
            source_rows[b.ocr_run_id]["canonical_sha256"],
            source_rows[b.ocr_run_id]["manifest_sha256"],
        )
        for b in bindings
    ):
        raise Conflict("Liên kết nguồn đã thay đổi.", code="publication_evidence_changed")
    snapshot_row, snapshot = await read(db, blob, run, "input_snapshot")
    expected = {
        "schema_version": "qnu.compiler.input/v1",
        "topic": run.topic,
        "documents": documents,
    }
    if snapshot != json_bytes(expected) or snapshot_row.sha256 != run.input_sha256:
        raise Conflict("Snapshot Compiler khác nguồn đã ghim.", code="publication_evidence_changed")
    draft_row, raw_draft = await read(db, blob, run, "draft_json")
    markdown_row, markdown = await read(db, blob, run, "markdown")
    content = json.loads(raw_draft)
    if (
        content.get("compilation_run_id") != run.id
        or content.get("citations") != citation_index(documents)
        or content.get("source_tables") != literal_tables(documents)
    ):
        raise Conflict("Nội dung không khớp bằng chứng.", code="publication_evidence_changed")
    if require_current:
        await assert_current_sources(
            db, workspace_id, collection_id, documents, allow_staged=allow_staged, serving=serving
        )
    bundle = digest(
        {
            "run_id": run.id,
            "request_hash": run.request_hash,
            "config": run.config,
            "input_sha256": run.input_sha256,
            "draft_sha256": draft_row.sha256,
            "markdown_sha256": markdown_row.sha256,
            "sources": [
                {k: v for k, v in d.items() if k not in {"pages", "evidence"}} for d in documents
            ],
        }
    )
    provenance = {
        "provider": (run.config or {}).get("provider"),
        "prompt_version": (run.config or {}).get("prompt_version"),
        "sources": [
            {
                "identity": d["identity"],
                "ocr_run_id": d["ocr_run_id"],
                "canonical_sha256": d["canonical_sha256"],
                "manifest_sha256": d["manifest_sha256"],
                **(
                    {
                        "text_version": d["text_version"],
                        "original_canonical_sha256": d["original_canonical_sha256"],
                    }
                    if "text_version" in d
                    else {}
                ),
            }
            for d in documents
        ],
    }
    if run.origin == "user_edit":
        provenance["origin"] = run.origin
        provenance["parent_run_id"] = run.parent_run_id
        provenance["edit"] = run.config["edit"]
    return VersionBundle(
        run.input_sha256,
        draft_row.sha256,
        markdown_row.sha256,
        bundle,
        provenance,
        content,
        markdown,
        documents,
    )


async def assert_current_sources(
    db: AsyncSession,
    workspace_id: str,
    collection_id: str,
    documents: list[dict],
    *,
    allow_staged: bool = False,
    serving: bool = False,
) -> None:
    for identity in [d["identity"] for d in documents]:
        source = await db.scalar(
            select(KBSource)
            .where(
                KBSource.id == identity["source_id"],
                KBSource.workspace_id == workspace_id,
                KBSource.collection_id == collection_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        valid = (
            {source.serving_revision_no if serving else source.latest_revision_no}
            if source
            else set()
        )
        if source and allow_staged:
            valid.add(source.latest_revision_no)
        if identity["revision_no"] not in valid:
            raise Conflict(
                "Nguồn có revision mới; cần biên soạn và duyệt lại.",
                code="publication_source_stale",
            )


def registered_bundle_hash(bundle: VersionBundle, annotations: list[dict]) -> str:
    if not annotations:
        return bundle.bundle_sha256
    from qnu.domains.knowledge.metadata import validate_annotations

    validate_annotations(annotations, bundle.content, bundle.documents)
    return digest(
        {"compiler_bundle_sha256": bundle.bundle_sha256, "retrieval_metadata": annotations}
    )


# Registration adds audit-only provenance; the compiler identity is every other key.
REGISTRATION_PROVENANCE_KEYS = frozenset({"automatic_metadata", "metadata_confirmation"})


def assert_pinned(version: CompiledVersion, bundle: VersionBundle) -> None:
    if (
        version.input_sha256,
        version.draft_sha256,
        version.markdown_sha256,
        version.bundle_sha256,
    ) != (
        bundle.input_sha256,
        bundle.draft_sha256,
        bundle.markdown_sha256,
        registered_bundle_hash(bundle, version.retrieval_metadata or []),
    ):
        raise Conflict(
            "Nội dung khác phiên bản đã đăng ký/duyệt.", code="publication_bundle_changed"
        )
    compiler_owned = {
        key: value
        for key, value in version.provenance.items()
        if key not in REGISTRATION_PROVENANCE_KEYS
    }
    if compiler_owned != bundle.provenance:
        raise Conflict("Provenance đã khác bản đã đăng ký.", code="publication_bundle_changed")
