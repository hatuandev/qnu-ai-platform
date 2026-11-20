"""A human acknowledges exact immutable review bytes; model verdict never approves."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.review import artifacts
from qnu.domains.knowledge.compilation.review.models import CompilationReview
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.knowledge.publication.models import CompiledVersion
from qnu.domains.knowledge.publication.schemas import (
    ReviewAcknowledgement,
    ReviewSkipAcknowledgement,
)
from qnu.platform.errors import Conflict, DependencyUnavailable
from qnu.ports.blob_store import BlobStore


async def check_spelling_in_progress(db: AsyncSession, target: CompiledVersion) -> dict | None:
    from qnu.domains.knowledge.compilation.models import CompilationInput
    from qnu.domains.ocr.models import utcnow
    from qnu.domains.ocr.review.models import SpellingRun

    inputs = (
        await db.scalars(
            select(CompilationInput).where(CompilationInput.run_id == target.compilation_run_id)
        )
    ).all()
    if inputs:
        active_spelling = await db.scalar(
            select(SpellingRun)
            .where(
                SpellingRun.run_id.in_([inp.ocr_run_id for inp in inputs]),
                SpellingRun.canonical_sha256.in_([inp.canonical_sha256 for inp in inputs]),
                SpellingRun.status == "running",
                SpellingRun.expires_at > utcnow(),
            )
            .order_by(SpellingRun.pass_number.desc(), SpellingRun.created_at.desc())
            .limit(1)
        )
        if active_spelling is not None:
            return {
                "pass_number": active_spelling.pass_number,
                "total_passes": active_spelling.total_passes,
                "pass_name": active_spelling.pass_name,
                "check_id": active_spelling.id,
            }
    return None


async def material(db: AsyncSession, blob: BlobStore, target: CompiledVersion) -> dict:
    compiler_hash = target.bundle_sha256
    if target.retrieval_metadata:
        from qnu.domains.knowledge.publication.evidence import assert_pinned, load_bundle

        bundle = await load_bundle(
            db, blob, target.workspace_id, target.collection_id, target.compilation_run_id
        )
        assert_pinned(target, bundle)
        compiler_hash = bundle.bundle_sha256
    row = await db.scalar(
        select(CompilationReview)
        .where(
            CompilationReview.workspace_id == target.workspace_id,
            CompilationReview.collection_id == target.collection_id,
            CompilationReview.compilation_run_id == target.compilation_run_id,
            CompilationReview.bundle_sha256 == compiler_hash,
            CompilationReview.input_sha256 == target.input_sha256,
            CompilationReview.draft_sha256 == target.draft_sha256,
        )
        .order_by(CompilationReview.created_at.desc(), CompilationReview.id.desc())
        .limit(1)
        .execution_options(populate_existing=True)
    )
    if row is None or row.status != "completed":
        raise Conflict(
            "Cần review hoàn tất của đúng phiên bản trước khi duyệt.",
            code="publication_review_required",
        )
    artifact, payload = await artifacts.read(db, blob, row, "report_json")
    try:
        report = json.loads(payload)
        if report["review_id"] != row.id or report["bundle_sha256"] != compiler_hash:
            raise ValueError("identity")
        findings = [{"finding_id": digest(item), "finding": item} for item in report["findings"]]
        if len({item["finding_id"] for item in findings}) != len(findings):
            raise ValueError("duplicate findings")
    except (ValueError, TypeError, KeyError, AssertionError) as exc:
        raise DependencyUnavailable(
            "Báo cáo review không khớp phiên bản.", code="publication_review_invalid"
        ) from exc

    spelling_details = await check_spelling_in_progress(db, target)
    return {
        "review_id": row.id,
        "report_sha256": artifact.sha256,
        "bundle_sha256": target.bundle_sha256,
        "verdict": row.verdict,
        "findings": findings,
        "spelling_in_progress": spelling_details is not None,
        "spelling_details": spelling_details,
    }


async def acknowledge(
    db: AsyncSession, blob: BlobStore, target: CompiledVersion, ack: ReviewAcknowledgement | None
) -> dict:
    if ack is None:
        raise Conflict(
            "Người duyệt phải xác nhận đã xem review.", code="publication_review_required"
        )
    if target.retrieval_metadata and ack.retrieval_metadata_sha256 != digest(
        target.retrieval_metadata
    ):
        raise Conflict(
            "Cần xác nhận đã xem đúng metadata của phiên bản.",
            code="publication_metadata_review_required",
        )
    current = await material(db, blob, target)
    expected = {item["finding_id"] for item in current["findings"]}
    supplied = [item.finding_id for item in ack.resolutions]
    if (ack.review_id, ack.report_sha256) != (current["review_id"], current["report_sha256"]):
        raise Conflict("Review đã đổi; cần xem và xác nhận lại.", code="publication_review_stale")
    if len(set(supplied)) != len(supplied) or set(supplied) != expected:
        raise Conflict(
            "Cần giải trình từng vấn đề đúng báo cáo; không nhận ID thừa hoặc trùng.",
            code="publication_review_unresolved",
        )
    return {**ack.model_dump(), "bundle_sha256": target.bundle_sha256}


def acknowledge_skip(target: CompiledVersion, skip: ReviewSkipAcknowledgement, reason: str) -> dict:
    """Called only after publication approve authorization, with immutable preview binding."""
    if skip.version_id != target.id or skip.bundle_sha256 != target.bundle_sha256:
        raise Conflict("Phiên bản đã đổi; cần xác nhận lại.", code="publication_review_stale")
    if target.retrieval_metadata and skip.retrieval_metadata_sha256 != digest(
        target.retrieval_metadata
    ):
        raise Conflict(
            "Cần xác nhận đúng metadata của phiên bản.",
            code="publication_metadata_review_required",
        )
    if len(reason.strip()) < 10:
        raise Conflict("Thiếu lý do bỏ qua review.", code="publication_review_required")
    return {
        **skip.model_dump(),
        "mode": "skipped",
        "reason": reason,
        "compilation_run_id": target.compilation_run_id,
    }


async def recheck(
    db: AsyncSession, blob: BlobStore, target: CompiledVersion, saved: dict | None
) -> None:
    if not saved or saved.get("bundle_sha256") != target.bundle_sha256:
        raise Conflict(
            "Chưa có xác nhận review khớp phiên bản; cần thu hồi và duyệt lại.",
            code="publication_review_required",
        )
    if saved.get("mode") == "skipped":
        fields = {key: saved.get(key) for key in ReviewSkipAcknowledgement.model_fields}
        skip = ReviewSkipAcknowledgement.model_validate(fields)
        if acknowledge_skip(target, skip, saved.get("reason", "")) != saved:
            raise Conflict("Xác nhận bỏ qua review đã đổi.", code="publication_review_stale")
        return
    fields = {key: value for key, value in saved.items() if key != "bundle_sha256"}
    await acknowledge(db, blob, target, ReviewAcknowledgement.model_validate(fields))
