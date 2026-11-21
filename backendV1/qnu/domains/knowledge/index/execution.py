"""Build a staged dense generation, then atomically activate only a current publication snapshot."""

from __future__ import annotations

import asyncio
import hashlib
import re

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.chunking import READABLE_CHUNKER_VERSIONS
from qnu.domains.knowledge.index.contextual import VERSION as CONTEXT_VERSION
from qnu.domains.knowledge.index.facts import project_table
from qnu.domains.knowledge.index.lease import (
    ClaimLost,
    assert_claim,
    claim,
    commit_owned,
    heartbeat,
)
from qnu.domains.knowledge.index.models import IndexChunk, IndexInput, IndexRun, IndexTableFact
from qnu.domains.knowledge.index.row_cards import (
    DocumentCardMeta,
    column_years_for_table,
    render_projection_to_cards,
)
from qnu.domains.knowledge.index.snapshots import assert_snapshot, publication_identity
from qnu.domains.knowledge.publication.access import authorize
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.embedding.runtime import resolve_embedding_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict, DependencyUnavailable
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.provider_execution import bind_usage
from qnu.ports.vector_store import VectorStore

logger = get_logger(__name__)


async def validate_target(db: AsyncSession, run: IndexRun, actor: AuthActor, vectors: VectorStore):
    await authorize(db, actor, run.workspace_id, run.collection_id, write=True)
    runtime = await resolve_embedding_runtime(db, run.workspace_id, run.provider_id)
    if (
        runtime.configuration_hash != run.config["provider"]["configuration_hash"]
        or vectors.target_hash != run.config["vector_target_hash"]
        or run.config["chunker_version"] not in READABLE_CHUNKER_VERSIONS
        or run.config.get("search_context_version") not in (None, CONTEXT_VERSION)
    ):
        raise Conflict(
            "Model/vector target/chunker đã thay đổi.", code="index_configuration_changed"
        )
    return runtime


async def _embed_pending(db, blob, run, actor, model: EmbeddingModel, vectors: VectorStore) -> None:
    rows = list(
        (
            await db.scalars(
                select(IndexChunk).where(IndexChunk.run_id == run.id).order_by(IndexChunk.ordinal)
            )
        ).all()
    )
    size = run.config["embedding_batch_size"]
    for start in range(0, len(rows), size):
        batch = [row for row in rows[start : start + size] if row.vector is None]
        if not batch:
            continue
        runtime = await validate_target(db, run, actor, vectors)
        await assert_snapshot(db, blob, actor, run)
        texts = [row.text for row in batch]
        budget = runtime.budget(texts)
        await assert_claim(db, run)
        request_hash = digest(
            {
                "run_id": run.id,
                "chunk_ids": [c.id for c in batch],
                "text_hashes": [c.text_sha256 for c in batch],
                "model": runtime.configuration_hash,
            }
        )
        usage = await usage_service.reserve(
            db,
            actor,
            run.workspace_id,
            "embedding",
            f"index:{run.id}:{start}",
            request_hash,
            budget,
            run.provider_id,
        )
        await assert_claim(db, run)
        run.pending_batch = {
            "start": start,
            "usage_id": usage.id,
            "chunk_ids": [c.id for c in batch],
        }
        await commit_owned(db, run)
        try:
            result = await model.embed(texts, bind_usage(runtime.request(), usage.id))
        except AppException:
            await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
            raise
        try:
            await assert_claim(db, run)
        except ClaimLost:
            # Account for a measured upstream response even when its job was cancelled.
            await usage_service.settle(db, usage.id, total_tokens=result.total_tokens, failed=True)
            raise
        raw_sha = hashlib.sha256(result.raw_body).hexdigest()
        raw_key = f"v1/workspaces/{run.workspace_id}/index/{run.id}/batches/{start}-{raw_sha}.json"
        try:
            await blob.put_bytes(raw_key, result.raw_body, "application/json")
        except Exception as exc:
            raise DependencyUnavailable(
                "Không lưu được phản hồi embedding.", code="storage_unavailable"
            ) from exc
        if result.dimension != run.dimension or len(result.vectors) != len(batch):
            raise Conflict(
                "Embedding không khớp số chunk/dimension.", code="embedding_dimension_mismatch"
            )
        for chunk, vector in zip(batch, result.vectors, strict=True):
            chunk.vector = vector
        run.batch_receipts = [
            *run.batch_receipts,
            {
                "start": start,
                "count": len(batch),
                "chunk_ids": [chunk.id for chunk in batch],
                "raw_key": raw_key,
                "raw_sha256": raw_sha,
                "usage_id": usage.id,
                "total_tokens": result.total_tokens,
            },
        ]
        run.pending_batch = None
        await commit_owned(db, run)
        await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
        logger.info(
            "index_batch_embedded",
            run_id=run.id,
            start=start,
            count=len(batch),
            dimension=run.dimension,
        )


async def _write_vectors(db, blob, run, actor, vectors: VectorStore) -> None:
    await validate_target(db, run, actor, vectors)
    await assert_snapshot(db, blob, actor, run)
    await assert_claim(db, run)
    await vectors.ensure_collection(run.vector_collection, run.dimension)
    rows = (
        await db.execute(
            select(IndexChunk, IndexInput)
            .join(IndexInput, IndexChunk.input_id == IndexInput.id)
            .where(IndexChunk.run_id == run.id)
            .order_by(IndexChunk.ordinal)
        )
    ).all()
    for start in range(0, len(rows), 64):
        points = []
        for chunk, binding in rows[start : start + 64]:
            if chunk.vector is None or len(chunk.vector) != run.dimension:
                raise Conflict("Chunk chưa có vector hoàn chỉnh.", code="index_vectors_incomplete")
            points.append(
                {
                    "id": chunk.point_id,
                    "vector": chunk.vector,
                    "payload": {
                        "run_id": run.id,
                        "workspace_id": run.workspace_id,
                        "collection_id": run.collection_id,
                        "version_id": binding.version_id,
                        "chunk_id": chunk.id,
                        "text_sha256": chunk.text_sha256,
                    },
                }
            )
        await assert_claim(db, run)
        await vectors.upsert(run.vector_collection, points)
    await commit_owned(db, run)


_column_years_for_table = column_years_for_table


async def _write_table_facts(db: AsyncSession, blob: BlobStore, run: IndexRun, actor: AuthActor) -> None:
    """Persist kb_index_table_facts + RowCard projection before atomic is_active=True swap."""
    published = await assert_snapshot(db, blob, actor, run)
    await assert_claim(db, run)
    bindings = {
        binding.document_id: binding
        for binding in (
            await db.scalars(select(IndexInput).where(IndexInput.run_id == run.id))
        ).all()
    }
    await db.execute(delete(IndexTableFact).where(IndexTableFact.index_run_id == run.id))
    total_facts = 0
    total_cards = 0
    for publication in published:
        binding = bindings.get(publication.document.id)
        if binding is None:
            continue
        annotations = [
            a.model_dump(mode="json", exclude_none=True)
            for a in publication.version.retrieval_metadata
        ]
        doc_title = publication.document.title
        doc_num_match = re.search(r"\b(\d+/[A-ZĐ]+(?:-[A-ZĐ]+)*)\b", doc_title)
        doc_year_match = re.search(r"\b(19\d\d|20\d\d)\b", doc_title)
        doc_meta = DocumentCardMeta(
            title=doc_title,
            doc_number=doc_num_match.group(1) if doc_num_match else "",
            doc_year=int(doc_year_match.group(1)) if doc_year_match else None,
        )
        tables = (
            publication.content.get("source_tables")
            or publication.content.get("tables")
            or []
        )
        last_opening_headers: dict[int, list[list[dict]]] = {}
        for entry in tables:
            table = entry.get("table") or {}
            citation = entry.get("citation") or ""
            if table.get("status") != "parsed" or not table.get("rows") or not citation:
                continue
            cols = table.get("column_count", 0)
            inherited = last_opening_headers.get(cols)
            p_num = entry.get("page_number") or entry.get("page")
            page_list = (
                [p_num]
                if isinstance(p_num, int)
                else (p_num if isinstance(p_num, list) else [])
            )
            heading_prefix = entry.get("heading") or entry.get("section_heading") or ""
            base_title = entry.get("title") or ""
            if heading_prefix and base_title and base_title != publication.document.title:
                table_title = f"{heading_prefix}: {base_title}"
            elif heading_prefix:
                table_title = heading_prefix
            elif base_title:
                table_title = base_title
            else:
                table_title = publication.document.title

            projected = project_table(
                table,
                table_id=citation,
                source_table_citation=citation,
                title=table_title,
                column_years=column_years_for_table(citation, annotations),
                inherited_header_rows=inherited,
            )
            if not projected.facts:
                continue
            if projected.has_header and projected.storage_mode == "facts" and not inherited:
                from qnu.domains.knowledge.index.table_layout import header_rows, table_structure

                st = table_structure(table)
                hr = header_rows(st)
                if not hr:
                    from qnu.domains.knowledge.index.table_dependencies import (
                        administrative_header,
                        header_row,
                        multitier_header,
                        typed_header,
                    )

                    multi = multitier_header(table)
                    if multi is not None:
                        hr = multi
                    elif (
                        typed_header(table)
                        or header_row(table)
                        or administrative_header(table)
                    ):
                        hr = [0]
                if hr:
                    last_opening_headers[cols] = [table["rows"][r] for r in hr]
            cards = render_projection_to_cards(
                projected,
                document_meta=doc_meta,
                page_numbers=page_list,
                max_chunk_bytes=run.config.get("chunk_max_bytes"),
            )
            total_cards += len(cards)
            serialized_notes = [note.model_dump(mode="json") for note in projected.scoped_notes]
            for fact in projected.facts:
                db.add(
                    IndexTableFact(
                        id=new_id("ft"),
                        input_id=binding.id,
                        index_run_id=run.id,
                        workspace_id=run.workspace_id,
                        collection_id=run.collection_id,
                        document_id=binding.document_id,
                        version_id=binding.version_id,
                        publication_decision_id=binding.publication_decision_id,
                        table_id=projected.table_id,
                        source_table_citation=projected.source_table_citation,
                        table_title=projected.title,
                        has_header=projected.has_header,
                        keep_whole_in_chunk=projected.keep_whole_in_chunk,
                        column_keys=list(projected.column_keys),
                        scoped_notes=serialized_notes,
                        fact_id=fact.fact_id,
                        row_index=fact.row_index,
                        row_kind=fact.row_kind,
                        row_pointer=fact.row_pointer,
                        group_name=fact.group,
                        subject_code=fact.subject_code,
                        subject_name=fact.subject_name,
                        data_year=fact.data_year,
                        data_status=fact.data_status,
                        attributes={
                            **{k: v.model_dump(mode="json") for k, v in fact.attributes.items()},
                            **(
                                {
                                    "_data_years": {
                                        "raw": ", ".join(str(y) for y in fact.data_years),
                                        "value_kind": "normal",
                                        "years": fact.data_years,
                                    }
                                }
                                if fact.data_years and len(fact.data_years) > 1
                                else {}
                            ),
                        },
                        detail_md_pointers=dict(fact.detail_md_pointers),
                        applicable_note_ids=list(fact.applicable_note_ids),
                        source_cell_refs=list(fact.source_cell_refs),
                        cross_references=list(fact.cross_references),
                    )
                )
                total_facts += 1
    await commit_owned(db, run)
    if total_facts:
        logger.info(
            "index_table_facts_written",
            run_id=run.id,
            facts=total_facts,
            row_cards=total_cards,
        )


async def _activate(db, blob, run, actor, vectors: VectorStore) -> str:
    await validate_target(db, run, actor, vectors)
    published = await assert_snapshot(db, blob, actor, run)
    if digest([publication_identity(p) for p in published]) != run.input_sha256:
        raise Conflict("Snapshot index không khớp publication.", code="index_publication_changed")
    if run.config.get("replacement_action_id"):
        from qnu.domains.lifecycle.replacement import activate_replacement

        published = await activate_replacement(db, blob, actor, run)
    chunks = list(
        (
            await db.scalars(
                select(IndexChunk).where(IndexChunk.run_id == run.id).order_by(IndexChunk.ordinal)
            )
        ).all()
    )
    manifest = {
        "schema_version": "qnu.index.manifest/v1",
        "run_id": run.id,
        "generation": run.generation,
        "inputs": [publication_identity(p) for p in published],
        "input_sha256": run.input_sha256,
        "config": run.config,
        "dimension": run.dimension,
        "vector_collection": run.vector_collection,
        "chunks": [
            {
                "id": c.id,
                "point_id": c.point_id,
                "text_sha256": c.text_sha256,
                "vector_sha256": digest(c.vector),
                "citations_sha256": digest(c.citations),
                "structure_sha256": digest(c.structure),
            }
            for c in chunks
        ],
        "batch_receipts": run.batch_receipts,
    }
    payload = json_bytes(manifest)
    sha = hashlib.sha256(payload).hexdigest()
    key = f"v1/workspaces/{run.workspace_id}/index/{run.id}/manifest/{sha}.json"
    try:
        await blob.put_bytes(key, payload, "application/json")
    except Exception as exc:
        raise DependencyUnavailable(
            "Không lưu được index manifest.", code="storage_unavailable"
        ) from exc
    await assert_claim(db, run)
    await db.execute(
        update(IndexRun)
        .where(
            IndexRun.collection_id == run.collection_id,
            IndexRun.id != run.id,
            IndexRun.is_active.is_(True),
        )
        .values(is_active=False, deactivated_at=utcnow())
    )
    run.manifest_key, run.manifest_sha256 = key, sha
    run.status, run.is_active, run.finished_at = "completed", True, utcnow()
    run.deactivated_at = None
    run.lease_expires_at = None
    run.error_code = None
    await record_workspace_event(
        db,
        workspace_id=run.workspace_id,
        actor=actor,
        action="index.activated",
        detail={"run_id": run.id, "manifest_sha256": sha, "chunks": run.chunks_total},
    )
    await commit_owned(db, run)
    return "completed"


async def execute_run(
    db: AsyncSession,
    blob: BlobStore,
    run_id: str,
    *,
    worker_id: str,
    model: EmbeddingModel,
    vectors: VectorStore,
) -> str:
    seconds = get_settings().INDEX_LEASE_SECONDS
    run = await claim(db, run_id, worker_id, seconds)
    if run is None:
        return "not_claimed"
    token = run.worker_id
    actor = background_actor(run.requested_by)
    async with heartbeat(run, seconds):
        try:
            if run.pending_batch is not None:
                await usage_service.settle(
                    db, run.pending_batch["usage_id"], total_tokens=None, failed=True
                )
                raise AppException("Worker bị ngắt khi embedding.", code="embedding_uncertain")
            if run.attempt_count > get_settings().INDEX_MAX_ATTEMPTS:
                raise Conflict("Đã hết số lần chạy index.", code="index_attempts_exhausted")
            for receipt in run.batch_receipts:
                await usage_service.settle(
                    db, receipt["usage_id"], total_tokens=receipt["total_tokens"]
                )
            await _embed_pending(db, blob, run, actor, model, vectors)
            await _write_vectors(db, blob, run, actor, vectors)
            await _write_table_facts(db, blob, run, actor)
            status = await _activate(db, blob, run, actor, vectors)
            logger.info(
                "index_completed", run_id=run.id, generation=run.generation, chunks=run.chunks_total
            )
            return status
        except asyncio.CancelledError:
            await db.rollback()
            raise
        except ClaimLost:
            await db.rollback()
            logger.warning("index_claim_lost", run_id=run_id)
            return "not_claimed"
        except Exception as exc:
            await db.rollback()
            run = await db.get(IndexRun, run_id, populate_existing=True)
            if run is None or run.worker_id != token:
                return "not_claimed"
            code = exc.code if isinstance(exc, AppException) else "index_failed"
            try:
                await assert_claim(db, run)
                uncertain = code == "embedding_uncertain" or (
                    run.pending_batch is not None
                    and code
                    not in {
                        "embedding_unreachable",
                        "embedding_auth_failed",
                        "embedding_rate_limited",
                        "embedding_unavailable",
                        "embedding_rejected",
                        "embedding_response_invalid",
                        "embedding_dimension_mismatch",
                        "embedding_vector_invalid",
                        "embedding_count_mismatch",
                        "embedding_model_mismatch",
                    }
                )
                retry = (
                    code in {"vector_unavailable", "storage_unavailable"}
                    and not uncertain
                    and run.attempt_count < get_settings().INDEX_MAX_ATTEMPTS
                )
                run.status = "uncertain" if uncertain else "queued" if retry else "failed"
                run.error_code = code
                if not retry:
                    from qnu.domains.lifecycle.replacement import fail_replacement

                    await fail_replacement(db, run, code)
                run.lease_expires_at = None
                run.finished_at = None if retry else utcnow()
                if retry:
                    run.dispatched_at = None
                await commit_owned(db, run)
                logger.warning("index_stopped", run_id=run.id, status=run.status, error_code=code)
                return run.status
            except ClaimLost:
                await db.rollback()
                return "not_claimed"
