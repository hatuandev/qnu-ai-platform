"""Durable source purge on the existing lifecycle receipt and V1 worker queue."""

import asyncio
import contextlib
import hashlib
import json
import re
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from sqlalchemy import select, update

from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.knowledge.preparation.models import (
    ACTIVE_PREPARATION_STATUSES,
    PreparationIntent,
)
from qnu.domains.lifecycle import effects
from qnu.domains.lifecycle.models import LifecycleAction, ResourceState
from qnu.domains.lifecycle.purge_graph import (
    delete_rows,
    graph_for_collection,
    graph_for_source,
    graph_plan,
    selected,
    table,
)
from qnu.domains.operations.jobs.catalog import SPECS
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.database import AsyncSessionFactory, Base
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger

logger = get_logger(__name__)
TASK = "source_purge_job"
PURGE_KINDS = ("source", "collection")


def is_purge_delete(row):
    return row.kind in PURGE_KINDS and row.action == "delete"


def _resource_detail(row) -> dict:
    key = "collection_id" if row.kind == "collection" else "source_id"
    return {"action_id": row.id, key: row.resource_id}


async def _graph_for(db, row):
    loader = graph_for_collection if row.kind == "collection" else graph_for_source
    return await loader(db, row.workspace_id, row.resource_id, allow_published=True)


async def inspect_purge(db, kind, resource, blob):
    loader = graph_for_collection if kind == "collection" else graph_for_source
    graph = await loader(db, resource.workspace_id, resource.id, allow_published=True)
    plan = graph_plan(graph)
    versions = graph.get("kb_compiled_versions", {}).values()
    published = [row["id"] for row in versions if row["status"] == "published"]
    return plan, {
        "collection_id": resource.id if kind == "collection" else resource.collection_id,
        "resource_label": resource.name if kind == "collection" else resource.title,
        "permanent": True,
        "originals_and_raw_evidence": "permanently_deleted",
        "restore_available": False,
        "files_to_delete": len(plan["objects"]),
        "sources_to_delete": len(graph.get("kb_sources", {})),
        "folders_to_delete": len(graph.get("kb_folders", {})),
        "compiled_versions_to_delete": len(plan["rows"].get("kb_compiled_versions", [])),
        "published_versions_to_withdraw": len(published),
        "published_version_ids": published,
        "backups_retained": True,
        "blob_target_hash": blob.target_hash,
    }


JOB_TABLES = {
    kind: SPECS[kind].model
    for kind in ("ocr", "compiler", "review", "auto_review", "spelling", "turn")
}


def _primary_key(model) -> str:
    return next(iter(model.__table__.primary_key.columns)).name


def _lease_text(value) -> str | None:
    return value.isoformat() if value is not None else None


async def _checkpoint(db, graph) -> list[dict]:
    """Record work that can still write before its status is changed to cancelled."""
    waiting: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def record(entry: dict) -> None:
        key = (entry["table"], entry["id"])
        if key in seen:
            return
        seen.add(key)
        waiting.append(entry)

    for model in JOB_TABLES.values():
        field = _primary_key(model)
        for row in graph.get(model.__tablename__, {}).values():
            if row.get("status") in ("queued", "running"):
                record(
                    {
                        "table": model.__tablename__,
                        "id": row[field],
                        "lease_expires_at": _lease_text(row.get("lease_expires_at")),
                    }
                )
    for row in graph.get("kb_preparation_intents", {}).values():
        if row.get("status") in ACTIVE_PREPARATION_STATUSES:
            record(
                {
                    "table": "kb_preparation_intents",
                    "id": row["id"],
                    "lease_expires_at": _lease_text(row.get("lease_expires_at")),
                }
            )
    run_ids = {row["run_id"] for row in graph.get("kb_index_inputs", {}).values()}
    run_ids |= {
        row["id"]
        for row in graph.get("kb_index_runs", {}).values()
        if row.get("status") in ("queued", "running")
    }
    if run_ids:
        for run in (
            await db.scalars(
                select(IndexRun).where(
                    IndexRun.id.in_(run_ids),
                    IndexRun.status.in_(("queued", "running")),
                )
            )
        ).all():
            record(
                {
                    "table": "kb_index_runs",
                    "id": run.id,
                    "lease_expires_at": _lease_text(run.lease_expires_at),
                }
            )
    return waiting


async def _checkpoint_open(db, checkpoint) -> bool:
    """A recorded task is still open while it can run or its worker lease is live."""
    for entry in checkpoint or []:
        table_name, row_id = entry.get("table"), entry.get("id")
        model = Base.metadata.tables.get(table_name)
        if model is None or not row_id:
            continue
        key = next(iter(model.primary_key.columns))
        columns = [model.c.status]
        has_lease = "lease_expires_at" in model.c
        if has_lease:
            columns.append(model.c.lease_expires_at)
        row = (await db.execute(select(*columns).where(key == row_id))).first()
        if row is None:
            continue
        if row[0] in ("queued", "running"):
            return True
        lease = row[1] if has_lease else None
        if lease is not None and lease > utcnow():
            return True
    return False


async def require_not_pending(db, workspace_id, kind, resource_id):
    if kind not in PURGE_KINDS:
        return
    pending = await db.scalar(
        select(LifecycleAction.id)
        .where(
            LifecycleAction.workspace_id == workspace_id,
            LifecycleAction.kind == kind,
            LifecycleAction.resource_id == resource_id,
            LifecycleAction.action == "delete",
            LifecycleAction.status == "pending",
        )
        .limit(1)
    )
    if pending:
        label = "Kho" if kind == "collection" else "Tài liệu"
        raise Conflict(f"{label} đang được xóa vĩnh viễn.", code=f"{kind}_purge_pending")


async def _cancel(db, graph) -> None:
    for kind in JOB_TABLES:
        spec = SPECS[kind]
        keys = graph.get(spec.model.__tablename__, {})
        if not keys:
            continue
        rows = (
            await db.scalars(
                select(spec.model)
                .where(
                    selected(spec.model.__table__, list(keys.values())),
                    spec.model.status.in_(("queued", "running")),
                )
                .with_for_update()
            )
        ).all()
        for job in rows:
            await effects.cancel_job(db, kind, job)
    # An active intent can still create an OCR or Compilation run after the stop;
    # it is cancelled before those children are snapshotted.
    intent_ids = [
        row["id"]
        for row in graph.get("kb_preparation_intents", {}).values()
        if row.get("status") in ACTIVE_PREPARATION_STATUSES
    ]
    if intent_ids:
        for intent in (
            await db.scalars(
                select(PreparationIntent)
                .where(
                    PreparationIntent.id.in_(intent_ids),
                    PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
                )
                .with_for_update()
            )
        ).all():
            await effects.cancel_job(db, "preparation", intent)
    # Only builders containing affected inputs are cancelled; unrelated jobs remain untouched.
    run_ids = {row["run_id"] for row in graph.get("kb_index_inputs", {}).values()}
    run_ids |= {row["id"] for row in graph.get("kb_index_runs", {}).values()}
    for run in (
        await db.scalars(
            select(IndexRun)
            .where(
                IndexRun.id.in_(run_ids),
                IndexRun.status.in_(("queued", "running")),
            )
            .with_for_update()
        )
    ).all():
        await effects.cancel_job(db, "index", run)


async def prepare(db, blob, vectors, actor, row, resource):
    # A persisted task re-resolves server authority; never copy JWT roles into a queue payload.
    await resolve_workspace_access(
        db,
        background_actor(actor_ref(actor)),
        row.workspace_id,
        required_roles=("admin",),
        for_update=True,
    )
    # Confirmed permanent deletion withdraws every related published version in
    # the same transaction; the assistant stops using the source before cleanup.
    await effects.withdraw(db, row, resource)
    checkpoint: list[dict] = []
    recorded: set[tuple[str, str]] = set()
    # Re-scan after cancellation so children created by a stopping coordinator are
    # recorded and stopped too; the bounded loop cannot chase an unbounded chain.
    for _ in range(3):
        graph = await _graph_for(db, row)
        discovered = [
            entry
            for entry in await _checkpoint(db, graph)
            if (entry["table"], entry["id"]) not in recorded
        ]
        if not discovered:
            break
        for entry in discovered:
            recorded.add((entry["table"], entry["id"]))
            checkpoint.append(entry)
        await _cancel(db, graph)
    resource_state = await db.get(ResourceState, (row.workspace_id, row.kind, row.resource_id))
    if resource_state is None:
        db.add(
            ResourceState(
                workspace_id=row.workspace_id,
                kind=row.kind,
                resource_id=row.resource_id,
                status="deleted",
            )
        )
    else:
        resource_state.status, resource_state.revision = "deleted", resource_state.revision + 1
    await db.flush()
    # Capture post-cancellation rows. Workers cannot create more source-derived work.
    settled = await _graph_for(db, row)
    plan = graph_plan(settled)
    plan["blob_target_hash"], plan["vector_target_hash"] = blob.target_hash, vectors.target_hash
    row.confirmed_by = row.confirmed_by or row.actor_ref
    waiting = await _checkpoint_open(db, checkpoint)
    row.phase = "waiting_for_workers" if waiting else "deleting_vectors"
    row.progress = {
        "step": "Đang dừng tác vụ" if waiting else "Bắt đầu dọn dữ liệu",
        "percent": None,
    }
    row.lease_expires_at, row.worker_id = None, None
    row.result = {
        "permanent": True,
        "phase": row.phase,
        "_purge_plan": plan,
        "checkpoint": {"jobs": checkpoint},
    }
    await record_workspace_event(
        db,
        workspace_id=row.workspace_id,
        actor=actor,
        action=f"{row.kind}.purge_accepted",
        detail=_resource_detail(row),
    )


async def dispatch(row, queue):
    if queue is None:
        return False
    try:
        return await queue.enqueue(
            TASK, row.id, job_id=f"qnu:v1:purge:{row.id}:{int(utcnow().timestamp()) // 60}"
        )
    except Exception:
        logger.warning("source_purge_dispatch_failed", action_id=row.id)
        return False


async def _delete_objects(blob, plan, workspace_id):
    # Validate every key before the first object is removed.
    for key in plan["objects"]:
        if not key.startswith(
            (
                f"v1/workspaces/{workspace_id}/",
                f"ocr-text/{workspace_id}/",
                f"ocr-spelling/{workspace_id}/",
            )
        ):
            raise Conflict("Object ngoài phạm vi xóa.", code="purge_scope_invalid")
    for key, expected in plan["objects"].items():
        if (
            await blob.exists(key)
            and expected
            and hashlib.sha256(await blob.get_bytes(key)).hexdigest() != expected
        ):
            raise Conflict("Object đã thay đổi so với lúc xác nhận.", code="purge_object_changed")
        await blob.purge(key)
        if await blob.exists(key):
            raise Conflict("Object vẫn còn trong storage.", code="purge_storage_failed")


async def _delete_vectors(db, vectors, graph):
    groups = {}
    for chunk in graph.get("kb_index_chunks", {}).values():
        groups.setdefault(chunk["run_id"], []).append(chunk["point_id"])
    for run_id, ids in groups.items():
        run = await db.get(IndexRun, run_id)
        if run is None or run.vectors_retired_at is not None:
            continue
        if run.config.get("vector_target_hash") != vectors.target_hash:
            raise Conflict("Vector target đã đổi; chưa xóa.", code="purge_target_changed")
        for offset in range(0, len(ids), 256):
            await vectors.delete_points(run.vector_collection, ids[offset : offset + 256])


async def _delete_collection_vectors(vectors, graph):
    """Every generation of the collection is retired whole, so its Qdrant collection goes too."""
    embedded = {chunk["run_id"] for chunk in graph.get("kb_index_chunks", {}).values()}
    for run in sorted(graph.get("kb_index_runs", {}).values(), key=lambda item: item["id"]):
        if run["id"] not in embedded:
            continue
        if (run.get("config") or {}).get("vector_target_hash") != vectors.target_hash:
            raise Conflict("Vector target đã đổi; chưa xóa.", code="purge_target_changed")
        await vectors.delete_collection(run["vector_collection"])


async def _delete_index_run_objects(blob, workspace_id, graph) -> None:
    """Sweep the retired generation prefixes so stale manifests and batches do not survive."""
    for run in graph.get("kb_index_runs", {}).values():
        prefix = f"v1/workspaces/{workspace_id}/index/{run['id']}/"
        for item in await blob.list_objects(prefix):
            await blob.purge(item.key)
            if await blob.exists(item.key):
                raise Conflict("Object vẫn còn trong storage.", code="purge_storage_failed")


INDEX_PREFIX = "v1/workspaces/{workspace_id}/index/"


async def _delete_index_objects(blob, workspace_id, keys) -> None:
    prefix = INDEX_PREFIX.format(workspace_id=workspace_id)
    for key in keys:
        if not key.startswith(prefix):
            raise Conflict("Object ngoài phạm vi xóa.", code="purge_scope_invalid")
    for key in keys:
        await blob.purge(key)
        if await blob.exists(key):
            raise Conflict("Object vẫn còn trong storage.", code="purge_storage_failed")


def _mapping_conflict(detail: str) -> Conflict:
    return Conflict(detail, code="purge_index_mapping_unverified")


def _ordered_raw(body: object, count: int) -> list[dict]:
    """Raw embedding entries are addressed by their own index, never by list order."""
    rows = body.get("data") if isinstance(body, dict) else None
    if not isinstance(rows, list) or len(rows) != count:
        raise _mapping_conflict("Không xác minh được ánh xạ embedding.")
    ordered: dict[int, dict] = {}
    for item in rows:
        index = item.get("index") if isinstance(item, dict) else None
        if type(index) is not int or index in ordered or not 0 <= index < count:
            raise _mapping_conflict("Không xác minh được ánh xạ embedding.")
        ordered[index] = item
    return [ordered[number] for number in range(count)]


def _verified_entries(
    body: object, chunk_ids: list[str], sealed_chunks: dict[str, dict], digest
) -> list[dict]:
    entries = _ordered_raw(body, len(chunk_ids))
    for entry, chunk_id in zip(entries, chunk_ids, strict=True):
        sealed = sealed_chunks.get(chunk_id)
        if (
            sealed is None
            or not isinstance(entry.get("embedding"), list)
            or digest(entry["embedding"]) != sealed["vector_sha256"]
        ):
            raise _mapping_conflict("Raw embedding không khớp manifest.")
    return entries


async def _filtered_batch_receipts(
    blob, run, sealed, removed, assert_owned: Callable[[], Awaitable[None]]
) -> tuple[list[dict], list[str]]:
    """Keep surviving embeddings, splitting or retiring raw receipts of the removed source."""
    from qnu.domains.knowledge.compilation.artifacts import json_bytes
    from qnu.domains.knowledge.publication.evidence import digest

    chunks = list(sealed.get("chunks") or [])
    sealed_chunks = {chunk["id"]: chunk for chunk in chunks}
    positions = {
        chunk.get("ordinal", position): chunk["id"] for position, chunk in enumerate(chunks)
    }
    receipts, cleanup = [], []
    for receipt in sealed.get("batch_receipts") or []:
        chunk_ids = receipt.get("chunk_ids")
        if chunk_ids is None:
            start, count = receipt.get("start"), receipt.get("count")
            if type(start) is not int or type(count) is not int or start < 0 or count <= 0:
                raise _mapping_conflict("Không xác minh được ánh xạ embedding.")
            chunk_ids = [positions.get(position) for position in range(start, start + count)]
        if (
            not isinstance(chunk_ids, list)
            or not all(isinstance(chunk_id, str) for chunk_id in chunk_ids)
            or len(chunk_ids) != receipt.get("count")
            or len(set(chunk_ids)) != len(chunk_ids)
        ):
            raise _mapping_conflict("Không xác minh được ánh xạ embedding.")
        key = receipt["raw_key"]
        payload = await blob.get_bytes(key)
        if hashlib.sha256(payload).hexdigest() != receipt.get("raw_sha256"):
            raise Conflict("Raw embedding đã thay đổi.", code="purge_object_changed")
        try:
            body = json.loads(payload)
        except ValueError as exc:
            raise _mapping_conflict("Raw embedding không phải JSON.") from exc
        entries = _verified_entries(body, chunk_ids, sealed_chunks, digest)
        kept = [chunk_id for chunk_id in chunk_ids if chunk_id not in removed]
        kept_entries = [
            entry
            for entry, chunk_id in zip(entries, chunk_ids, strict=True)
            if chunk_id not in removed
        ]
        if not kept:
            cleanup.append(key)
            continue
        if len(kept_entries) == len(entries):
            receipts.append({**receipt, "count": len(kept), "chunk_ids": kept})
            continue
        body["data"] = [{**entry, "index": number} for number, entry in enumerate(kept_entries)]
        derived = json_bytes(body)
        raw_sha = hashlib.sha256(derived).hexdigest()
        raw_key = (
            f"v1/workspaces/{run.workspace_id}/index/{run.id}"
            f"/batches/{receipt['start']}-{raw_sha}.json"
        )
        await assert_owned()
        await blob.put_bytes(raw_key, derived, "application/json")
        receipts.append(
            {
                **receipt,
                "count": len(kept),
                "raw_key": raw_key,
                "raw_sha256": raw_sha,
                "chunk_ids": kept,
            }
        )
        cleanup.append(key)
    return receipts, cleanup


async def _unsealed_index_evidence(db, run) -> dict:
    from qnu.domains.knowledge.publication.evidence import digest

    if not run.batch_receipts:
        return {}
    chunks = await db.execute(
        select(IndexChunk.id, IndexChunk.ordinal, IndexChunk.vector)
        .where(IndexChunk.run_id == run.id, IndexChunk.workspace_id == run.workspace_id)
        .order_by(IndexChunk.ordinal)
    )
    return {
        "batch_receipts": run.batch_receipts,
        "chunks": [
            {"id": chunk_id, "ordinal": ordinal, "vector_sha256": digest(vector)}
            for chunk_id, ordinal, vector in chunks
        ],
    }


async def _uncommitted_batch_keys(blob, run, removed_chunks) -> list[str]:
    """Find raw files written by an interrupted batch before its SQL commit."""
    pending = run.pending_batch
    if not pending or not removed_chunks.intersection(pending["chunk_ids"]):
        return []
    committed = {receipt["raw_key"] for receipt in run.batch_receipts}
    prefix = f"v1/workspaces/{run.workspace_id}/index/{run.id}/batches/"
    name = re.compile(rf"{pending['start']}-[0-9a-f]{{64}}\.json")
    return [
        item.key
        for item in await blob.list_objects(prefix)
        if name.fullmatch(item.key.removeprefix(prefix)) and item.key not in committed
    ]


async def _finish_index_cleanup(db, blob, row, token: str) -> None:
    keys = (row.result or {}).get("_purge_cleanup")
    if not keys:
        return
    # Hold the receipt lock through storage cleanup so a replacement cannot
    # acquire it while the old worker is still deleting checkpointed objects.
    await _fence(db, row.id, token, {})
    await _delete_index_objects(blob, row.workspace_id, keys)
    result = {key: value for key, value in row.result.items() if key != "_purge_cleanup"}
    await _fence(db, row.id, token, {"result": result})
    await db.commit()


async def _reseal_indexes(db, blob, graph, action_id, token: str):
    """Keep surviving generations exact: manifest, receipts and raw vectors move together."""
    from qnu.domains.knowledge.compilation.artifacts import json_bytes
    from qnu.domains.knowledge.index.search import manifest
    from qnu.domains.knowledge.publication.evidence import digest

    row = await db.get(LifecycleAction, action_id, populate_existing=True)
    if row is None:
        return

    async def assert_owned() -> None:
        await _fence(db, action_id, token, {})

    await _finish_index_cleanup(db, blob, row, token)
    chunks = list(graph.get("kb_index_chunks", {}).values())
    inputs = list(graph.get("kb_index_inputs", {}).values())
    cleanup: list[str] = []
    touched = False
    for run_id in sorted({item["run_id"] for item in inputs}):
        run = await db.scalar(
            select(IndexRun)
            .where(IndexRun.id == run_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if run is None:
            continue
        removed_chunks = {item["id"] for item in chunks if item["run_id"] == run_id}
        if not run.manifest_key:
            evidence = await _unsealed_index_evidence(db, run)
            receipts, retired = await _filtered_batch_receipts(
                blob, run, evidence, removed_chunks, assert_owned
            )
            if receipts != run.batch_receipts:
                run.batch_receipts = receipts
                touched = True
            cleanup.extend(retired)
            cleanup.extend(await _uncommitted_batch_keys(blob, run, removed_chunks))
            continue
        sealed = await manifest(db, blob, run)
        removed_versions = {item["version_id"] for item in inputs if item["run_id"] == run_id}
        remaining_inputs = [
            item
            for item in sealed.get("inputs") or []
            if item["version_id"] not in removed_versions
        ]
        remaining_chunks = [
            item for item in sealed.get("chunks") or [] if item["id"] not in removed_chunks
        ]
        receipts, retired = await _filtered_batch_receipts(
            blob, run, sealed, removed_chunks, assert_owned
        )
        cleanup += retired
        if sealed.get("purge", {}).get("action_id") == action_id:
            # Already resealed for this receipt; a retry only finishes file cleanup.
            run.input_sha256, run.chunks_total = digest(remaining_inputs), len(remaining_chunks)
            run.batch_receipts = receipts
            touched = True
            continue
        updated = {
            **sealed,
            "inputs": remaining_inputs,
            "chunks": remaining_chunks,
            "batch_receipts": receipts,
            "input_sha256": digest(remaining_inputs),
            "purge": {"action_id": action_id, "previous_manifest_sha256": run.manifest_sha256},
        }
        payload = json_bytes(updated)
        sha = hashlib.sha256(payload).hexdigest()
        key = f"v1/workspaces/{run.workspace_id}/index/{run.id}/manifest/{sha}.json"
        await assert_owned()
        await blob.put_bytes(key, payload, "application/json")
        run.manifest_key, run.manifest_sha256 = key, sha
        run.input_sha256, run.chunks_total = updated["input_sha256"], len(remaining_chunks)
        run.batch_receipts = receipts
        touched = True
    if cleanup or touched:
        result = row.result or {}
        if cleanup:
            # Persist the exact keys with the derived manifest so a storage outage
            # resumes without re-deriving from evidence that is already gone.
            result = {**result, "_purge_cleanup": sorted(set(cleanup))}
        # The ownership check and all SQL mutations above commit together.
        await _fence(db, action_id, token, {"result": result})
        await db.commit()
    if cleanup:
        row = await db.get(LifecycleAction, action_id, populate_existing=True)
        await _finish_index_cleanup(db, blob, row, token)


def _settled_plan(plan, graph):
    current = graph_plan(graph)
    if current["graph_sha256"] == plan["graph_sha256"]:
        return plan
    outputs = {
        "ocr_run_pages": ("run_id", "ocr_processing_runs"),
        "ocr_run_artifacts": ("run_id", "ocr_processing_runs"),
        "kb_compilation_artifacts": ("run_id", "kb_compilation_runs"),
        "kb_compilation_outputs": ("run_id", "kb_compilation_runs"),
        "kb_compilation_segment_artifacts": ("segment_id", "kb_compilation_segments"),
        "kb_compilation_review_artifacts": ("review_id", "kb_compilation_reviews"),
        "kb_compilation_review_segment_artifacts": (
            "segment_id",
            "kb_compilation_review_segments",
        ),
    }
    # In-flight calls may retain raw evidence after cancellation, within the
    # exact approved runs. New sources, versions or jobs never widen this intent.
    for name in set(plan["rows"]) | set(current["rows"]):
        before, after = plan["rows"].get(name, []), current["rows"].get(name, [])
        if name not in outputs:
            if before != after:
                raise Conflict("Phụ thuộc đã đổi; chưa xóa.", code="purge_dependency_changed")
            continue
        parent_field, parent_table = outputs[name]
        parents = {row["id"] for row in plan["rows"].get(parent_table, [])}
        if any(item not in after for item in before) or any(
            row[parent_field] not in parents for row in graph.get(name, {}).values()
        ):
            raise Conflict("Artifact ngoài các tác vụ đã xác nhận.", code="purge_scope_invalid")
    for key, sha in plan["objects"].items():
        if key not in current["objects"] or (sha and sha != current["objects"][key]):
            raise Conflict("Object đã thay đổi.", code="purge_object_changed")
    output_objects = graph_plan(
        {name: values for name, values in graph.items() if name in outputs}
    )["objects"]
    if set(current["objects"]) - set(plan["objects"]) - set(output_objects):
        raise Conflict("Object ngoài các tác vụ đã xác nhận.", code="purge_scope_invalid")
    return {**plan, **current}


PURGE_LEASE_SECONDS = 120


class _ClaimLost(Exception):
    """The receipt lease no longer belongs to this worker."""


def _progress(step: str, percent: int | None) -> dict:
    return {"step": step, "percent": percent}


async def _fence(db, action_id: str, token: str, values: dict) -> None:
    """Renew ownership and write progress in one fenced statement."""
    now = utcnow()
    owned = await db.scalar(
        update(LifecycleAction)
        .where(
            LifecycleAction.id == action_id,
            LifecycleAction.status == "pending",
            LifecycleAction.worker_id == token,
            LifecycleAction.lease_expires_at.is_not(None),
            LifecycleAction.lease_expires_at > now,
        )
        .values(
            lease_expires_at=now + timedelta(seconds=PURGE_LEASE_SECONDS),
            **values,
        )
        .returning(LifecycleAction.id)
    )
    if owned is None:
        raise _ClaimLost


def _heartbeat(action_id: str, token: str) -> asyncio.Task:
    async def pulse():
        while True:
            await asyncio.sleep(max(PURGE_LEASE_SECONDS // 3, 1))
            try:
                async with AsyncSessionFactory() as beat:
                    now = utcnow()
                    renewed = await beat.scalar(
                        update(LifecycleAction)
                        .where(
                            LifecycleAction.id == action_id,
                            LifecycleAction.status == "pending",
                            LifecycleAction.worker_id == token,
                            LifecycleAction.lease_expires_at.is_not(None),
                            LifecycleAction.lease_expires_at > now,
                        )
                        .values(lease_expires_at=now + timedelta(seconds=PURGE_LEASE_SECONDS))
                        .returning(LifecycleAction.id)
                    )
                    await beat.commit()
                    if renewed is None:
                        return
            except Exception:
                logger.warning("source_purge_heartbeat_failed", action_id=action_id)
                return

    return asyncio.create_task(pulse())


async def _record_failure(db, action_id: str, token: str, exc: Exception) -> str:
    row = await db.scalar(
        select(LifecycleAction)
        .where(LifecycleAction.id == action_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None or row.status != "pending" or row.worker_id not in (None, token):
        # A replacement worker owns the receipt; its lease and error state stay intact.
        await db.commit()
        return "pending"
    row.error_code = exc.code if isinstance(exc, AppException) else f"{row.kind}_purge_failed"
    row.last_error_at = utcnow()
    row.lease_expires_at, row.worker_id = None, None
    row.progress = {
        **(row.progress or {}),
        "step": "Tạm dừng do lỗi; có thể tiếp tục cùng biên nhận",
    }
    await db.commit()
    return "pending"


async def execute(db, blob, vectors, action_id):
    initial = await db.get(LifecycleAction, action_id)
    if initial is None or not is_purge_delete(initial) or initial.status != "pending":
        return "not_pending"
    workspace_id, actor = initial.workspace_id, background_actor(initial.actor_ref)
    token = f"purge:{uuid.uuid4().hex}"
    heartbeat: asyncio.Task | None = None
    try:
        await resolve_workspace_access(
            db, actor, workspace_id, required_roles=("admin",), for_update=True
        )
        row = await db.scalar(
            select(LifecycleAction)
            .where(LifecycleAction.id == action_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None or row.status != "pending":
            return row.status if row else "not_pending"
        now = utcnow()
        lease = getattr(row, "lease_expires_at", None)
        if lease is not None and lease > now:
            return "not_claimed"
        row.worker_id, row.lease_expires_at = token, now + timedelta(seconds=PURGE_LEASE_SECONDS)
        row.attempt_count = (getattr(row, "attempt_count", 0) or 0) + 1
        await db.commit()
        heartbeat = _heartbeat(action_id, token)

        result = row.result or {}
        legacy_wait = result.get("not_before")
        if legacy_wait and datetime.fromisoformat(legacy_wait) > now:
            row.phase = "waiting_for_workers"
            row.result = {**result, "phase": row.phase}
            row.lease_expires_at, row.worker_id = None, None
            await db.commit()
            return "waiting_for_cancelled_work"
        if await _checkpoint_open(db, (result.get("checkpoint") or {}).get("jobs")):
            row.phase = "waiting_for_workers"
            row.progress = _progress("Đang chờ tác vụ đã dừng kết thúc", None)
            row.result = {**result, "phase": row.phase}
            # A deferral must not hold the receipt lease; resumption or takeover stays possible.
            row.lease_expires_at, row.worker_id = None, None
            await db.commit()
            return "waiting_for_cancelled_work"
        plan = result["_purge_plan"]
        if (
            blob.target_hash != plan["blob_target_hash"]
            or vectors.target_hash != plan["vector_target_hash"]
        ):
            raise Conflict("Storage/vector target đã đổi; chưa xóa.", code="purge_target_changed")
        graph = await _graph_for(db, row)
        plan = _settled_plan(plan, graph)
        await _assert_exclusive_blobs(db, plan)
        await _fence(
            db,
            action_id,
            token,
            {"phase": "deleting_vectors", "progress": _progress("Đang xóa vector", 25)},
        )
        await db.commit()
        if row.kind == "collection":
            await _delete_collection_vectors(vectors, graph)
        else:
            await _delete_vectors(db, vectors, graph)
        await _fence(
            db,
            action_id,
            token,
            {
                "phase": "deleting_objects",
                "progress": _progress("Đang xóa tệp và bản dẫn xuất", 55),
            },
        )
        await db.commit()
        await _delete_objects(blob, plan, workspace_id)
        if row.kind == "collection":
            await _fence(
                db,
                action_id,
                token,
                {
                    "phase": "deleting_indexes",
                    "progress": _progress("Đang xóa chỉ mục của kho", 80),
                },
            )
            await db.commit()
            await _delete_index_run_objects(blob, workspace_id, graph)
        else:
            await _fence(
                db,
                action_id,
                token,
                {"phase": "resealing", "progress": _progress("Đang cập nhật chỉ mục còn lại", 80)},
            )
            await db.commit()
            await _reseal_indexes(db, blob, graph, row.id, token)
        plan = {**plan, **graph_plan(graph)}
        await _fence(
            db,
            action_id,
            token,
            {"phase": "deleting_rows", "progress": _progress("Đang hoàn tất biên nhận", 95)},
        )
        await db.commit()
        await delete_rows(db, plan, workspace_id)
        completed_result = {
            "permanent": True,
            "originals_retained": False,
            "restore_available": False,
            "files_deleted": len(plan["objects"]),
            "backups_retained": True,
            "phase": "completed",
        }
        if row.kind == "collection":
            completed_result["sources_deleted"] = len(plan["rows"].get("kb_sources", []))
            completed_result["folders_deleted"] = len(plan["rows"].get("kb_folders", []))
        completed = await db.scalar(
            update(LifecycleAction)
            .where(
                LifecycleAction.id == action_id,
                LifecycleAction.status == "pending",
                LifecycleAction.worker_id == token,
                LifecycleAction.lease_expires_at.is_not(None),
                LifecycleAction.lease_expires_at > utcnow(),
            )
            .values(
                status="completed",
                finished_at=utcnow(),
                error_code=None,
                phase="completed",
                progress=_progress("Đã xóa vĩnh viễn", 100),
                lease_expires_at=None,
                worker_id=None,
                result=completed_result,
            )
            .returning(LifecycleAction.id)
        )
        if completed is None:
            await db.rollback()
            return "not_claimed"
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action=f"{row.kind}.purged",
            detail={
                **_resource_detail(row),
                "confirmed_by": getattr(row, "confirmed_by", None),
                "takeover_by": getattr(row, "takeover_by", None),
            },
        )
        await db.commit()
        return "completed"
    except _ClaimLost:
        await db.rollback()
        logger.warning("source_purge_claim_lost", action_id=action_id)
        return "not_claimed"
    except asyncio.CancelledError:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        await _record_failure(db, action_id, token, exc)
        logger.warning(
            "source_purge_incomplete", action_id=action_id, error_type=type(exc).__name__
        )
        return "pending"
    finally:
        if heartbeat is not None:
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat


async def takeover(db, actor, workspace_id, action_id) -> LifecycleAction:
    """Another workspace admin resumes the same receipt; the original confirmer stays."""
    await resolve_workspace_access(
        db, actor, workspace_id, required_roles=("admin",), for_update=True
    )
    row = await db.scalar(
        select(LifecycleAction)
        .where(
            LifecycleAction.id == action_id,
            LifecycleAction.workspace_id == workspace_id,
            LifecycleAction.kind.in_(PURGE_KINDS),
            LifecycleAction.action == "delete",
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise Conflict("Không tìm thấy lượt xóa.", code="lifecycle_action_not_found")
    if row.status != "pending":
        raise Conflict("Lượt xóa đã kết thúc.", code="lifecycle_transition_invalid")
    if row.lease_expires_at is not None and row.lease_expires_at > utcnow():
        raise Conflict("Lượt xóa đang được xử lý.", code="purge_lease_active")
    row.confirmed_by = row.confirmed_by or row.actor_ref
    row.takeover_by = actor_ref(actor)
    row.takeover_at = utcnow()
    row.actor_ref = actor_ref(actor)
    row.lease_expires_at, row.worker_id = None, None
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action=f"{row.kind}.purge_takeover",
        detail={
            **_resource_detail(row),
            "confirmed_by": row.confirmed_by,
            "takeover_by": row.takeover_by,
        },
    )
    await db.commit()
    return row


async def _assert_exclusive_blobs(db, plan):
    for name, fields in {
        "kb_source_revisions": ("storage_key",),
        "ocr_run_pages": ("image_key", "raw_key"),
        "ocr_run_artifacts": ("blob_key",),
        "kb_compilation_artifacts": ("blob_key",),
        "kb_compilation_outputs": ("draft_blob_key", "markdown_blob_key"),
        "kb_compilation_segment_artifacts": ("blob_key",),
        "kb_compilation_review_artifacts": ("blob_key",),
        "kb_compilation_review_segment_artifacts": ("blob_key",),
        "ocr_text_versions": ("document_key", "markdown_key"),
    }.items():
        target = table(name)
        for field in fields:
            if await db.scalar(
                select(target.c[field])
                .where(
                    target.c[field].in_(list(plan["objects"])),
                    ~selected(target, plan["rows"].get(name, [])),
                )
                .limit(1)
            ):
                raise Conflict(
                    "Object còn được tài liệu khác tham chiếu.", code="purge_shared_object"
                )


async def source_purge_job(ctx, action_id):
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        return await execute(db, container.blob_store, container.vector_store, action_id)


async def reconcile(ctx):
    async with AsyncSessionFactory() as db:
        rows = (
            await db.scalars(
                select(LifecycleAction)
                .where(
                    LifecycleAction.kind.in_(PURGE_KINDS),
                    LifecycleAction.action == "delete",
                    LifecycleAction.status == "pending",
                )
                .order_by(LifecycleAction.created_at)
                .limit(50)
            )
        ).all()
        return sum(
            [
                int(await dispatch(row, ctx["container"].job_queue))
                for row in rows
                if (row.result or {}).get("permanent")
            ]
        )
