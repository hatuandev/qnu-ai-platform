"""Use cases for OCR processing runs: request, inspect, dispatch and read evidence.

A run is always addressed through its full chain (workspace → collection → source →
revision → run), and the caller must already have passed ``resolve_workspace_access``.
Reads never accept a storage path from the client: the artifact kind is the address.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import pymupdf
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.public_api import RevisionScope
from qnu.domains.modelops.public_api import resolve_ocr_runtime
from qnu.domains.modelops.resilience.routing import choose_target
from qnu.domains.ocr.config import (
    SUPPORTED_PROCESSING_EXTENSIONS,
    config_payload,
    processing_config,
)
from qnu.domains.ocr.execution import (
    TASK_NAME,
    job_id_for,
    read_artifact_bytes,
)
from qnu.domains.ocr.ids import new_id
from qnu.domains.ocr.models import (
    ACTIVE_RUN_STATUSES,
    OcrProcessingRun,
    OcrRunArtifact,
    OcrRunPage,
)
from qnu.domains.ocr.telemetry import observe_stage, run_identity
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict, EntityNotFound, UnsupportedMedia
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RequestOutcome:
    run: OcrProcessingRun
    created: bool
    dispatched: bool


class ProcessingService:
    async def request_run(
        self,
        db: AsyncSession,
        actor: AuthActor,
        scope: RevisionScope,
        *,
        provider_id: str | None,
        job_queue: JobQueue | None,
        force: bool = False,
        strategy: str = "ocr",
        commit: bool = True,
    ) -> RequestOutcome:
        if scope.extension not in SUPPORTED_PROCESSING_EXTENSIONS:
            raise UnsupportedMedia(
                f"Định dạng '{scope.extension or 'không rõ'}' chưa được hỗ trợ xử lý OCR.",
                code="processing_unsupported_format",
            )

        config = processing_config(get_settings(), scope.extension)
        payload = config_payload(config)
        if provider_id:
            payload["provider_requested"] = provider_id
        fingerprint = config.fingerprint
        if strategy == "auto":
            from qnu.domains.ocr.native import NATIVE_VERSION

            payload["extraction"] = {
                "strategy": "auto",
                "version": NATIVE_VERSION,
                "pymupdf": pymupdf.version[0],
            }
            fingerprint = hashlib.sha256(
                (fingerprint + json.dumps(payload["extraction"], sort_keys=True)).encode()
            ).hexdigest()

        active = await self._active_run(db, scope.revision_id)
        if active is not None:
            same_request = (
                active.config_fingerprint == fingerprint
                and (active.config or {}).get("provider_requested") == provider_id
            )
            if same_request:
                return RequestOutcome(
                    run=active, created=False, dispatched=active.dispatched_at is not None
                )
            raise Conflict(
                "Đã có lượt xử lý đang chạy cho phiên bản này.",
                code="processing_run_active",
            )

        if not force:
            reusable = await self._reusable_run(
                db, scope.workspace_id, scope.revision_id, fingerprint, provider_id
            )
            if reusable is not None:
                # Same revision, same pinned config, same provider and already complete:
                # re-running would only burn provider quota for identical evidence.
                return RequestOutcome(
                    run=reusable,
                    created=False,
                    dispatched=reusable.dispatched_at is not None,
                )

        generation = await self._next_generation(db, scope.revision_id)
        run = OcrProcessingRun(
            id=new_id("ocr"),
            workspace_id=scope.workspace_id,
            collection_id=scope.collection_id,
            source_id=scope.source_id,
            revision_id=scope.revision_id,
            revision_no=scope.revision_no,
            source_sha256=scope.sha256,
            generation=generation,
            status="queued",
            config=payload,
            config_fingerprint=fingerprint,
            requested_by=actor_ref(actor),
            pages_done=0,
            pages_failed=0,
            attempt_count=0,
            max_attempts=get_settings().OCR_RUN_MAX_ATTEMPTS,
        )
        db.add(run)
        await record_workspace_event(
            db,
            workspace_id=scope.workspace_id,
            actor=actor,
            action="source.processing_requested",
            detail={
                "collection_id": scope.collection_id,
                "source_id": scope.source_id,
                "revision_id": scope.revision_id,
                "run_id": run.id,
                "generation": generation,
            },
        )
        try:
            if commit:
                await db.commit()
            else:
                await db.flush()
        except IntegrityError as exc:
            if not commit:
                raise
            await db.rollback()
            raise Conflict(
                "Đã có lượt xử lý khác được tạo cho phiên bản này.",
                code="processing_run_active",
            ) from exc
        await db.refresh(run)

        logger.info("ocr_run_requested", **run_identity(run))
        dispatched = await self.dispatch(db, run, job_queue) if commit else False
        return RequestOutcome(run=run, created=True, dispatched=dispatched)

    async def dispatch(
        self, db: AsyncSession, run: OcrProcessingRun, job_queue: JobQueue | None
    ) -> bool:
        """Enqueue after commit; a queue outage leaves a queued run, never a lost one."""
        if job_queue is None or not get_settings().OCR_DISPATCH_ENABLED:
            return False
        if run.status not in ACTIVE_RUN_STATUSES:
            return False
        try:
            with observe_stage(run, "dispatch", logger=logger):
                await job_queue.enqueue(
                    TASK_NAME, run.id, job_id=job_id_for(run.id, run.attempt_count + 1)
                )
        except Exception:
            logger.warning("ocr_dispatch_failed", run_id=run.id)
            return False
        run.dispatched_at = run.dispatched_at or func.now()
        await db.commit()
        await db.refresh(run)
        return True

    async def list_runs(
        self, db: AsyncSession, workspace_id: str, revision_id: str, page: int, page_size: int
    ) -> tuple[list[OcrProcessingRun], int]:
        condition = (
            OcrProcessingRun.workspace_id == workspace_id,
            OcrProcessingRun.revision_id == revision_id,
        )
        total = int(
            (
                await db.execute(
                    select(func.count()).select_from(OcrProcessingRun).where(*condition)
                )
            ).scalar_one()
        )
        rows = (
            (
                await db.execute(
                    select(OcrProcessingRun)
                    .where(*condition)
                    .order_by(OcrProcessingRun.generation.desc())
                    .limit(page_size)
                    .offset((page - 1) * page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_run(
        self, db: AsyncSession, workspace_id: str, revision_id: str, run_id: str
    ) -> OcrProcessingRun:
        stmt = select(OcrProcessingRun).where(
            OcrProcessingRun.id == run_id,
            OcrProcessingRun.revision_id == revision_id,
            OcrProcessingRun.workspace_id == workspace_id,
        )
        run = (await db.execute(stmt)).scalars().first()
        if run is None:
            raise EntityNotFound("Không tìm thấy lượt xử lý.", code="processing_run_not_found")
        return run

    async def page_rows(self, db: AsyncSession, run_id: str) -> dict[int, OcrRunPage]:
        rows = (
            await db.execute(
                select(OcrRunPage)
                .where(OcrRunPage.run_id == run_id)
                .order_by(OcrRunPage.page_number)
            )
        ).scalars()
        return {row.page_number: row for row in rows}

    async def read_document(
        self, db: AsyncSession, blob_store: BlobStore, run: OcrProcessingRun
    ) -> tuple[str, bytes]:
        self._require_completed(run)
        record, payload = await self._require_artifact(db, blob_store, run, "canonical_json")
        return record.sha256, payload

    async def read_markdown(
        self, db: AsyncSession, blob_store: BlobStore, run: OcrProcessingRun
    ) -> bytes:
        self._require_completed(run)
        _, payload = await self._require_artifact(db, blob_store, run, "markdown")
        return payload

    async def read_manifest(
        self, db: AsyncSession, blob_store: BlobStore, run: OcrProcessingRun
    ) -> dict:
        _, payload = await self._require_artifact(db, blob_store, run, "manifest")
        return json.loads(payload)

    async def read_rendered_pdf(
        self, db: AsyncSession, blob_store: BlobStore, run: OcrProcessingRun
    ) -> tuple[str, bytes]:
        record, payload = await self._require_artifact(db, blob_store, run, "render_pdf", 0)
        return record.sha256, payload

    async def read_page_image(
        self, db: AsyncSession, blob_store: BlobStore, run: OcrProcessingRun, page_number: int
    ) -> tuple[str, bytes]:
        record, payload = await self._require_artifact(
            db, blob_store, run, "page_image", page_number
        )
        return record.sha256, payload

    async def read_page_raw(
        self, db: AsyncSession, blob_store: BlobStore, run: OcrProcessingRun, page_number: int
    ) -> tuple[str, bytes]:
        """Read original provider bytes, including evidence from failed runs."""
        record, payload = await read_artifact_bytes(
            db, blob_store, run, "raw_response", page_number
        )
        return record.sha256, payload

    async def snapshot(
        self, db: AsyncSession, blob_store: BlobStore, run: OcrProcessingRun
    ) -> dict:
        """Pinned evidence snapshot: identity, hashes, artifact list, mapping and verdict."""
        self._require_completed(run)
        manifest = await self.read_manifest(db, blob_store, run)
        canonical_sha, payload = await self.read_document(db, blob_store, run)
        canonical = json.loads(payload)
        # The manifest cannot list its own checksum, so the snapshot lists every stored
        # artifact from the database and exposes the manifest hash on its own field.
        artifacts = (
            (
                await db.execute(
                    select(OcrRunArtifact)
                    .where(OcrRunArtifact.run_id == run.id)
                    .order_by(OcrRunArtifact.kind, OcrRunArtifact.page_no)
                )
            )
            .scalars()
            .all()
        )
        return {
            "run_id": run.id,
            "generation": run.generation,
            "status": run.status,
            "identity": canonical["identity"],
            "processing": canonical["processing"],
            "canonical_sha256": canonical_sha,
            "manifest_sha256": next(
                (item.sha256 for item in artifacts if item.kind == "manifest"), None
            ),
            "checks": manifest["checks"],
            "validation": manifest["validation"],
            "artifacts": [
                {
                    "kind": item.kind,
                    "page_no": item.page_no,
                    "sha256": item.sha256,
                    "size_bytes": item.size_bytes,
                    "content_type": item.content_type,
                    "blob_key": item.blob_key,
                }
                for item in artifacts
            ],
            "pages": [
                {
                    "page_number": page["page_number"],
                    "status": page["status"],
                    "image_sha256": page["image"]["sha256"],
                    "blocks": len(page["blocks"]),
                }
                for page in canonical["pages"]
            ],
            "evidence": canonical["evidence"],
        }

    # ------------------------------------------------------------------ internals
    def _require_completed(self, run: OcrProcessingRun) -> None:
        """A failed or uncertain run has evidence but no usable result to serve."""
        if run.status != "completed":
            raise Conflict(
                f"Lượt xử lý chưa hoàn tất (trạng thái: {run.status}).",
                code="run_not_completed",
            )

    async def _active_run(self, db: AsyncSession, revision_id: str) -> OcrProcessingRun | None:
        stmt = select(OcrProcessingRun).where(
            OcrProcessingRun.revision_id == revision_id,
            OcrProcessingRun.status.in_(ACTIVE_RUN_STATUSES),
        )
        return (await db.execute(stmt)).scalars().first()

    async def _reusable_run(
        self,
        db: AsyncSession,
        workspace_id: str,
        revision_id: str,
        fingerprint: str,
        provider_id: str | None,
    ) -> OcrProcessingRun | None:
        """Newest completed run that this exact request would reproduce.

        A failed or uncertain run is never reusable: it holds evidence of an attempt,
        not a result, so asking again must create a new generation.
        """
        stmt = (
            select(OcrProcessingRun)
            .where(
                OcrProcessingRun.revision_id == revision_id,
                OcrProcessingRun.status == "completed",
                OcrProcessingRun.config_fingerprint == fingerprint,
            )
            .order_by(OcrProcessingRun.generation.desc())
            .limit(5)
        )
        for candidate in (await db.execute(stmt)).scalars():
            if (candidate.config or {}).get("provider_requested") == provider_id:
                if candidate.config.get("extraction") and candidate.provider_id is None:
                    return candidate
                selected, _ = await choose_target(db, workspace_id, "ocr", provider_id)
                runtime = await resolve_ocr_runtime(db, workspace_id, selected)
                pinned = (candidate.config or {}).get("provider") or {}
                if pinned.get("configuration_hash") == runtime.configuration_hash:
                    return candidate
        return None

    async def _next_generation(self, db: AsyncSession, revision_id: str) -> int:
        current = (
            await db.execute(
                select(func.max(OcrProcessingRun.generation)).where(
                    OcrProcessingRun.revision_id == revision_id
                )
            )
        ).scalar_one()
        return int(current or 0) + 1

    async def _require_artifact(
        self,
        db: AsyncSession,
        blob_store: BlobStore,
        run: OcrProcessingRun,
        kind: str,
        page_no: int = 0,
    ):
        try:
            return await read_artifact_bytes(db, blob_store, run, kind, page_no)
        except AppException as exc:
            if exc.code == "artifact_not_found":
                raise Conflict(
                    f"Lượt xử lý chưa có artifact '{kind}' (trạng thái: {run.status}).",
                    code="run_not_ready",
                ) from exc
            raise


processing_service = ProcessingService()
