"""Read-only listing of source revisions, their bindings, provenance and standard artifact state."""

import argparse
import asyncio
import json

from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", required=True)
    args = parser.parse_args()

    async with AsyncSessionFactory() as db:
        bindings = list((await db.scalars(
            select(KnowledgeBinding).where(KnowledgeBinding.collection_id == args.collection)
        )).all())
        binding_ids = {binding.id for binding in bindings}
        pending = {binding.repository_document_id: binding.id for binding in bindings if binding.status == "pending"}
        revisions = list((await db.scalars(
            select(KnowledgeSourceRevision).where(KnowledgeSourceRevision.binding_id.in_(binding_ids))
        )).all())

    for revision in sorted(revisions, key=lambda row: (row.binding_id, row.revision_no)):
        standard = (revision.snapshot_metadata or {}).get("qnu_markdown") or {}
        print(json.dumps({
            "binding_id": revision.binding_id, "revision_id": revision.id, "revision_no": revision.revision_no,
            "status": revision.status, "document": standard.get("document"), "renderer": standard.get("renderer_version"),
            "origin_file_hash": revision.origin_file_hash,
            "parser_profile": (revision.parse_provenance or {}).get("parser_profile"),
            "ocr_engine": (revision.parse_provenance or {}).get("ocr_engine"),
            "quality": (revision.quality_report or {}).get("overall_status"),
            "review_required": (revision.quality_report or {}).get("structured_review_required"),
            "unresolved_cells": standard.get("unresolved_cell_count"), "standard_status": standard.get("status"),
            "snapshot": revision.snapshot_storage_path,
            "binding_status": pending.get(revision.origin_document_id, "not-pending"),
        }, ensure_ascii=True))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
