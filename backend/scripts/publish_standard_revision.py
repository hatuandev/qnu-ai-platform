"""Publish one explicitly operator-approved, revision-bound standard source.

Does not approve uncertain cells, change models, restart services or publish other sources.
"""

import argparse
import asyncio
import json
import logging

from starlette.requests import Request

from app.core.database import AsyncSessionFactory, engine
from app.modules.auth.dependencies import get_current_actor
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.schemas import PublishVectorItem
from app.modules.knowledge.services.qnu_serving import verify_revision_pair
from app.modules.knowledge.services.selected_vector_publish import publish_selected_vectors
from app.modules.knowledge.services.source_artifact import get_source_artifact
from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
from app.modules.knowledge.services.vector_generation_service import vector_generation_service


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--binding", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    logging.disable(logging.ERROR)
    try:
        actor = await get_current_actor(Request({"type": "http", "headers": []}))
        if not args.approved or not args.reason.strip() or not all(actor.has_permission(permission) for permission in (
            "ai.knowledge.review", "ai.knowledge.publish", "ai.knowledge.update"
        )):
            raise ValueError("Explicit revision approval and server operator permissions required")
        async with AsyncSessionFactory() as db:
            binding = await db.get(KnowledgeBinding, args.binding)
            revision = await db.get(KnowledgeSourceRevision, args.revision)
            if (not binding or binding.collection_id != args.collection or not revision
                    or revision.binding_id != binding.id):
                raise ValueError("Source identity mismatch")
            await verify_revision_pair(revision)
            artifact = get_source_artifact(revision)
            if artifact.get("issues") or artifact.get("unresolved_cell_count"):
                raise ValueError("Uncertain extraction is not eligible for this operator workflow")
            if revision.status != "ready" or (artifact.get("review") or {}).get("status") != "approved":
                await source_ingestion_service.review_source_revision(db, args.collection, binding.id,
                    revision.id, "approved", comment=args.reason, actor_id=actor.actor_id)
            # API review/build normally use separate sessions. Drop loaded old relationships
            # when the operator executes those same lifecycle steps in one process.
            db.expunge_all()
            collection = await db.get(KnowledgeCollection, args.collection)
            generation_id = (collection.collection_metadata or {}).get("active_vector_generation_id")
            if not generation_id:
                raise ValueError("No configured active vector generation")
            index = await vector_generation_service.build_generation_for_source(
                db, args.collection, binding.id, generation_id,
                chunk_strategy=binding.chunk_strategy or "ClauseBasedChunker",
                expected_source_revision_id=revision.id)
            result = await publish_selected_vectors(db, args.collection, generation_id, [PublishVectorItem(
                binding_id=binding.id, source_revision_id=revision.id, index_revision_id=index.id)], actor)
            binding = await db.get(KnowledgeBinding, args.binding, populate_existing=True)
            if binding.active_index_revision_id != index.id:
                raise ValueError("Publication readback mismatch")
            print(json.dumps({"source_revision_id": revision.id, "index_revision_id": index.id,
                "chunk_count": index.chunk_count, "parity": index.parity_report.get("parity_passed"),
                "publication_epoch": result.new_epoch, "status": index.status}), flush=True)
    except Exception as error:
        print(json.dumps({"status": "failed", "code": getattr(error, "code", type(error).__name__),
                          "reason": (getattr(error, "details", None) or {}).get("reason")}), flush=True)
        raise SystemExit(1) from None
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
