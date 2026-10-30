"""Store JSON/Markdown generations; the run pointer moves only after both verify.

Partial generations stay readable for progress and resume but are never referenced
by ``run.output_id``, so publication and ``load_bundle`` cannot pick them up.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.models import CompilationOutput, CompilationRun
from qnu.domains.ocr.ids import new_id
from qnu.platform.errors import Conflict, DependencyUnavailable
from qnu.ports.blob_store import BlobStore


async def latest(
    db: AsyncSession, run_id: str, *, partial: bool | None = None
) -> CompilationOutput | None:
    query = select(CompilationOutput).where(CompilationOutput.run_id == run_id)
    if partial is not None:
        query = query.where(CompilationOutput.partial.is_(partial))
    return await db.scalar(
        query.order_by(CompilationOutput.generation.desc()).limit(1)
    )


async def _put_verified(
    blob: BlobStore, key: str, payload: bytes, content_type: str
) -> tuple[str, int]:
    try:
        await blob.put_bytes(key, payload, content_type)
        stored = await blob.get_bytes(key)
    except Exception as exc:
        raise DependencyUnavailable(
            "Không lưu được bản nháp Compiler.", code="storage_unavailable"
        ) from exc
    digest = hashlib.sha256(payload).hexdigest()
    if len(stored) != len(payload) or hashlib.sha256(stored).hexdigest() != digest:
        raise DependencyUnavailable(
            "Bản nháp Compiler lưu không khớp checksum.",
            code="compilation_output_mismatch",
        )
    return digest, len(payload)


async def store_output(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    *,
    draft_payload: bytes,
    markdown_payload: bytes,
    coverage: dict,
    partial: bool,
) -> CompilationOutput:
    """Write one immutable generation; never mix a JSON from one merge with old Markdown."""
    current = await db.scalar(
        select(func.max(CompilationOutput.generation)).where(
            CompilationOutput.run_id == run.id
        )
    )
    generation = int(current or 0) + 1
    output_id = new_id("cout")
    # An uncommitted writer must never overwrite a generation selected by its successor.
    prefix = (
        f"v1/workspaces/{run.workspace_id}/compilation/{run.id}/outputs/{output_id}"
    )
    draft_sha, _ = await _put_verified(
        blob, f"{prefix}/draft.json", draft_payload, "application/json"
    )
    markdown_sha, _ = await _put_verified(
        blob,
        f"{prefix}/markdown.md",
        markdown_payload,
        "text/markdown; charset=utf-8",
    )
    row = CompilationOutput(
        id=output_id,
        run_id=run.id,
        generation=generation,
        partial=partial,
        draft_blob_key=f"{prefix}/draft.json",
        draft_sha256=draft_sha,
        markdown_blob_key=f"{prefix}/markdown.md",
        markdown_sha256=markdown_sha,
        coverage=coverage,
    )
    db.add(row)
    await db.flush()
    if not partial:
        # Only a fully merged, verified pair becomes the run's publication candidate.
        run.output_id = row.id
    return row


async def read_output(
    db: AsyncSession, blob: BlobStore, row: CompilationOutput
) -> tuple[bytes, bytes]:
    try:
        draft = await blob.get_bytes(row.draft_blob_key)
        markdown = await blob.get_bytes(row.markdown_blob_key)
    except Exception as exc:
        raise DependencyUnavailable(
            "Không đọc được bản nháp Compiler.", code="compilation_output_missing"
        ) from exc
    if hashlib.sha256(draft).hexdigest() != row.draft_sha256 or (
        hashlib.sha256(markdown).hexdigest() != row.markdown_sha256
    ):
        raise Conflict(
            "Bản nháp Compiler không khớp checksum đã lưu.",
            code="compilation_output_mismatch",
        )
    return draft, markdown
