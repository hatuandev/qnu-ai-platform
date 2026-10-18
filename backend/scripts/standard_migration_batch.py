"""Local operator migration using existing lifecycle services; no invented reviewer identity.

Inspect first. Purge requires the exact inventory fingerprint and explicit backup waiver.
Import uses current code in a leased worker task, never approves extracted content.
"""

import argparse
import asyncio
import hashlib
import json
import logging

from arq import Retry
from sqlalchemy import select
from starlette.requests import Request

from app.core.database import AsyncSessionFactory, engine
from app.core.redis import get_redis_client
from app.core.storage import storage_service
from app.modules.assistants.models import AssistantModel
from app.modules.auth.dependencies import get_current_actor
from app.modules.documents.models import RepositoryDocument
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.schemas import KnowledgeImportBatchCreateRequest
from app.modules.knowledge.services.import_batch_service import import_batch_service
from app.modules.knowledge.services.migration_inventory import build_inventory
from app.modules.knowledge.services.qnu_serving import verify_revision_pair
from app.modules.knowledge.services.source_artifact import get_source_artifact
from app.modules.knowledge.services.source_pause import pause_source
from app.modules.knowledge.services.source_purge import (
    request_purge,
    snapshot_paths,
    validate_snapshot_paths,
)
from app.workers.tasks import task_knowledge_source_ingestion, task_knowledge_source_purge


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


async def inspect(db, collection_id: str) -> dict:
    inventory = await build_inventory(db, collection_id)
    collection = await db.get(KnowledgeCollection, collection_id)
    docs = list((await db.scalars(select(RepositoryDocument).order_by(RepositoryDocument.id))).all())
    assistants = list((await db.scalars(select(AssistantModel).order_by(AssistantModel.id))).all())
    revisions = list((await db.scalars(select(KnowledgeSourceRevision).join(
        KnowledgeBinding, KnowledgeSourceRevision.binding_id == KnowledgeBinding.id).where(
        KnowledgeBinding.collection_id == collection_id))).all())
    for revision in revisions:
        validate_snapshot_paths(snapshot_paths(revision), collection_id, revision.binding_id)
    return {"collection_id": collection_id, "inventory_fingerprint": digest(inventory["bindings"] + inventory["revisions"]),
            "bindings": inventory["bindings"], "revisions": len(revisions), "busy_jobs": inventory["busy_jobs"],
            "repository": [{"id": doc.id, "name": doc.file_name, "type": doc.file_type,
                            "hash": doc.file_hash, "active": doc.is_active} for doc in docs],
            "repository_fingerprint": digest([(doc.id, doc.file_hash, doc.storage_path, doc.row_version) for doc in docs]),
            "collection_config_hash": digest(collection.collection_metadata),
            "assistant_config_hash": digest([(assistant.id, assistant.config) for assistant in assistants])}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inspect", "purge", "import", "status"])
    parser.add_argument("--collection", required=True)
    parser.add_argument("--expected-inventory")
    parser.add_argument("--without-backup", action="store_true")
    parser.add_argument("--document-id", action="append", default=[])
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    logging.disable(logging.ERROR)  # Operator output is allowlisted metadata, not raw parser/provider exceptions.
    redis = get_redis_client()
    try:
        actor = await get_current_actor(Request({"type": "http", "headers": []}))
        permission = "ai.knowledge.delete" if args.action == "purge" else "ai.knowledge.update"
        if not actor.authenticated or not actor.has_permission(permission):
            raise ValueError("Operator permission required")
        async with AsyncSessionFactory() as db:
            before = await inspect(db, args.collection)
            if args.action == "inspect":
                print(json.dumps(before, ensure_ascii=True), flush=True)
                return
            if args.action == "purge":
                if not args.without_backup or args.expected_inventory != before["inventory_fingerprint"]:
                    raise ValueError("Exact inventory fingerprint and explicit backup waiver required")
                if before["busy_jobs"]:
                    raise ValueError("Collection has busy jobs")
                await storage_service.save("snapshots/migration-inventory/batch528-before.json", json.dumps(before).encode())
                for binding in before["bindings"]:
                    if binding["status"] == "detached":
                        continue
                    await pause_source(db, binding["id"], actor)
                    job = await request_purge(db, binding["id"], actor, dispatch=False)
                    await task_knowledge_source_purge({}, job.id)
                    print(json.dumps({"purged_binding": binding["id"], "job_id": job.id}), flush=True)
                after = await inspect(db, args.collection)
                for key in ("repository_fingerprint", "collection_config_hash", "assistant_config_hash"):
                    if after[key] != before[key]:
                        raise ValueError("Preservation mismatch: " + key)
                await storage_service.save("snapshots/migration-inventory/batch528-after-purge.json", json.dumps(after).encode())
                print(json.dumps({"remaining_revisions": after["revisions"], "preserved_config_repository": True}), flush=True)
            elif args.action == "import":
                if not args.document_id:
                    raise ValueError("Explicit Repository document IDs required")
                batch = await import_batch_service.create_import_batch(
                    args.collection, KnowledgeImportBatchCreateRequest(document_ids=args.document_id),
                    idempotency_key="standard528-" + digest(sorted(args.document_id)), created_by=actor.actor_id,
                    db=db, dispatch=False)
                if args.retry_failed:
                    batch = await import_batch_service.retry_failed_items(
                        args.collection, batch.id, db=db, dispatch=False)
                jobs = list((await db.scalars(select(JobRecord).where(
                    JobRecord.collection_id == args.collection, JobRecord.job_type == "knowledge_source_ingestion",
                    JobRecord.payload["batch_id"].astext == batch.id))).all())
                print(json.dumps({"batch_id": batch.id, "jobs": len(jobs)}), flush=True)
                failed_count = 0
                for job in jobs:
                    if job.status not in ("queued", "running"):
                        continue
                    try:
                        result = await task_knowledge_source_ingestion({"redis": redis}, job.id)
                    except Retry:
                        print(json.dumps({"job_id": job.id, "status": "owned_by_existing_worker"}), flush=True)
                        continue
                    except Exception as error:
                        failed_count += 1
                        print(json.dumps({"job_id": job.id, "status": "failed",
                            "code": getattr(error, "code", type(error).__name__),
                            "reason": (getattr(error, "details", None) or {}).get("reason")}), flush=True)
                        continue
                    print(json.dumps({key: result.get(key) for key in (
                        "status", "job_id", "source_revision_id", "source_status")}), flush=True)
                if failed_count:
                    raise SystemExit(1)
            else:
                revisions = list((await db.scalars(select(KnowledgeSourceRevision).join(
                    KnowledgeBinding, KnowledgeSourceRevision.binding_id == KnowledgeBinding.id).where(
                    KnowledgeBinding.collection_id == args.collection))).all())
                for revision in revisions:
                    standard = (revision.snapshot_metadata or {}).get("qnu_markdown") or {}
                    pair_valid = False
                    if standard.get("status") == "ready":
                        await verify_revision_pair(revision)
                        pair_valid = True
                    artifact = get_source_artifact(revision)
                    print(json.dumps({"binding_id": revision.binding_id, "revision_id": revision.id,
                        "status": revision.status, "standard_status": standard.get("status"),
                        "canonical_format": revision.canonical_format, "pair_valid": pair_valid,
                        "quality": (revision.quality_report or {}).get("overall_status"),
                        "unresolved_cells": artifact.get("unresolved_cell_count", 0),
                        "issues": sorted({issue.get("code", "unknown") for issue in artifact.get("issues", [])}),
                        "blocks": (standard.get("validation") or {}).get("block_count")},
                        ensure_ascii=True), flush=True)
    except Exception as error:
        print(json.dumps({"status": "failed", "code": getattr(error, "code", type(error).__name__)}), flush=True)
        raise SystemExit(1) from None
    finally:
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
