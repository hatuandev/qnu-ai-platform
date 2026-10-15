"""Dry-run by default; --apply inserts only an isolated review_required source revision."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory, engine
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.services.native_table_review import (
    create_native_table_draft,
    extract_native_evidence,
    replace_tables_only,
)


async def protected_state(db: AsyncSession, collection_id: str) -> str:
    state = []
    for sql in (
        "SELECT id,active_source_revision_id,active_index_revision_id,status FROM knowledge_bindings WHERE collection_id=:id ORDER BY id",
        "SELECT id,index_epoch,collection_metadata FROM knowledge_collections WHERE id=:id",
        "SELECT count(*) FROM knowledge_chunks WHERE collection_id=:id",
        "SELECT count(*) FROM knowledge_facts WHERE collection_id=:id",
        "SELECT id,canonical_hash,status,parse_provenance FROM knowledge_source_revisions WHERE id IN (SELECT active_source_revision_id FROM knowledge_bindings WHERE collection_id=:id) ORDER BY id",
    ):
        state.append([dict(row) for row in (await db.execute(text(sql), {"id": collection_id})).mappings()])
    return hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


async def run(args: argparse.Namespace) -> None:
    if args.output.exists():
        raise ValueError("Use a fresh output directory; previous reports must be preserved")
    args.output.mkdir(parents=True)
    content = args.pdf.read_bytes()
    native, numeric_count = await asyncio.to_thread(extract_native_evidence, content)
    try:
        async with AsyncSessionFactory() as db:
            if not args.apply:
                await db.execute(text("SET TRANSACTION READ ONLY"))
            before = await protected_state(db, args.collection)
            base = await db.get(KnowledgeSourceRevision, args.base)
            if base is None or base.binding_id != args.source or base.origin_file_hash != hashlib.sha256(content).hexdigest():
                raise ValueError("Selected PDF/base/source do not match")
            markdown, edits = replace_tables_only(base.canonical_markdown, native, len(base.page_manifest))
            report = {"status": "dry_run", "base_revision_id": base.id, "source_id": args.source,
                "origin_file_hash": base.origin_file_hash, "numeric_cells_verified": numeric_count,
                "tables": [{"page": item["page_number"], "columns": len(item["headers"]), "rows": len(item["rows"])} for item in native],
                "changes": [{k: v for k, v in edit.items() if k != "replacement"} for edit in edits],
                "protected_before": before}
            (args.output / "candidate.md").write_text(markdown, encoding="utf-8")
            (args.output / "native_cells.json").write_text(json.dumps(native, ensure_ascii=False, indent=2), encoding="utf-8")
            if args.apply:
                revision = await create_native_table_draft(db, collection_id=args.collection, source_id=args.source,
                    base_revision_id=args.base, tenant_id=args.tenant, workspace_id=args.workspace, content=content)
                report.update(status=revision.status, revision_id=revision.id, revision_no=revision.revision_no,
                    artifact_fact_count=len(revision.parse_provenance["structured_artifact"]["facts"]),
                    canonical_hash=revision.canonical_hash)
            after = await protected_state(db, args.collection)
            if before != after:
                raise ValueError("Protected publication/source/config/facts/chunks changed; transaction not committed")
            report.update(protected_after=after, protected_unchanged=True)
            if args.apply:
                await db.commit()
            else:
                await db.rollback()
        (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), flush=True)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    asyncio.run(run(parser.parse_args()))
