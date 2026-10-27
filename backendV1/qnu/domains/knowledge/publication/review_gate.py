"""A human acknowledges exact immutable review bytes; model verdict never approves."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.review import artifacts
from qnu.domains.knowledge.compilation.review.models import CompilationReview
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.knowledge.publication.models import CompiledVersion
from qnu.domains.knowledge.publication.schemas import ReviewAcknowledgement
from qnu.platform.errors import Conflict, DependencyUnavailable
from qnu.ports.blob_store import BlobStore


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
    return {
        "review_id": row.id,
        "report_sha256": artifact.sha256,
        "bundle_sha256": target.bundle_sha256,
        "verdict": row.verdict,
        "findings": findings,
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


async def recheck(
    db: AsyncSession, blob: BlobStore, target: CompiledVersion, saved: dict | None
) -> None:
    if not saved or saved.get("bundle_sha256") != target.bundle_sha256:
        raise Conflict(
            "Chưa có xác nhận review khớp phiên bản; cần thu hồi và duyệt lại.",
            code="publication_review_required",
        )
    fields = {key: value for key, value in saved.items() if key != "bundle_sha256"}
    await acknowledge(db, blob, target, ReviewAcknowledgement.model_validate(fields))
