"""Remove unchanged legacy sample content only; default is a read-only preview.

Run with --apply to back up matching records to storage and remove their vectors/DB rows.
Never deletes uploaded Repository files, collection settings, or ModelOps configuration.
"""

import argparse
import asyncio
import hashlib
import json
import uuid
from collections.abc import Iterator
from typing import Any

from qdrant_client import models as qm
from sqlalchemy import delete, func, select

from app.core.database import AsyncSessionFactory, engine
from app.core.redis import semantic_cache
from app.core.storage import storage_service
from app.main import app  # noqa: F401 — register all ORM mappings
from app.modules.knowledge import seeder
from app.modules.knowledge.models import (
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeDocument,
    KnowledgeFact,
)
from app.modules.rag.vector_indexer import vector_indexer


def sample_definitions() -> Iterator[tuple[str, str, list[dict[str, Any]], list[dict[str, Any]]]]:
    for prefix in ("DECREE_30", "REGULATIONS", "ADMISSIONS", "LIBRARY", "QUESTION_BANK"):
        yield tuple(getattr(seeder, f"{prefix}_{field}") for field in
                    ("COLLECTION_ID", "DOCUMENT_ID", "CHUNKS", "FACTS"))


def is_unchanged_sample(
    doc: KnowledgeDocument, chunks: list[KnowledgeChunk], facts: list[KnowledgeFact],
    expected_chunks: list[dict[str, Any]], expected_facts: list[dict[str, Any]],
) -> bool:
    expected_hash = hashlib.sha256("\n\n".join(c["content"] for c in expected_chunks).encode()).hexdigest()
    chunk_content = {c["id"]: c["content"] for c in expected_chunks}
    fact_values = {(f["entity_name"], f["attribute_name"], f.get("value", f.get("attribute_value")))
                   for f in expected_facts}
    return (doc.file_hash == expected_hash and doc.repository_document_id is None
            and all(chunk_content.get(c.id) == c.content and not c.index_revision_id for c in chunks)
            and all((f.entity_name, f.attribute_name, f.attribute_value) in fact_values
                    and not f.index_revision_id for f in facts))


def serialize_row(row: KnowledgeDocument | KnowledgeCollection | KnowledgeChunk | KnowledgeFact) -> dict[str, Any]:
    return {column.key: getattr(row, column.key) for column in row.__table__.columns}


async def clear_samples(apply: bool = False) -> None:
    backup_path = f"maintenance/knowledge-seed-backups/{uuid.uuid4().hex}.json"
    async with AsyncSessionFactory() as db:
        records = []
        for collection_id, document_id, expected_chunks, expected_facts in sample_definitions():
            col = (await db.execute(select(KnowledgeCollection).where(
                KnowledgeCollection.id == collection_id,
                KnowledgeCollection.tenant_id == seeder.DEFAULT_SEED_TENANT_ID,
                KnowledgeCollection.workspace_id == seeder.DEFAULT_SEED_WORKSPACE_ID,
            ).with_for_update())).scalar_one_or_none()
            doc = await db.get(KnowledgeDocument, document_id)
            if not col or not doc or doc.collection_id != collection_id:
                continue
            chunks = list((await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))).scalars().all())
            facts = list((await db.execute(select(KnowledgeFact).where(KnowledgeFact.document_id == document_id))).scalars().all())
            if not is_unchanged_sample(doc, chunks, facts, expected_chunks, expected_facts):
                raise RuntimeError(f"Refusing to remove modified sample {document_id}; nothing committed.")
            records.append((col, doc, chunks, facts))
        print(json.dumps([{ "document": d.id, "chunks": len(c), "facts": len(f)}
                          for _, d, c, f in records]))
        if not apply or not records:
            return
        backup = [{"collection": serialize_row(col), "document": serialize_row(doc),
                   "chunks": [serialize_row(c) for c in chunks], "facts": [serialize_row(f) for f in facts]}
                  for col, doc, chunks, facts in records]
        await storage_service.save(backup_path, json.dumps(backup, ensure_ascii=False, default=str).encode("utf-8"))
        for col, doc, _, _ in records:
            # Exact legacy namespace + document filter; never drops a collection/generation.
            namespace = vector_indexer._get_collection_name(col.id)
            if await vector_indexer.client.collection_exists(namespace):
                await vector_indexer.client.delete(collection_name=namespace, wait=True,
                    points_selector=qm.FilterSelector(filter=qm.Filter(must=[
                        qm.FieldCondition(key="document_id", match=qm.MatchValue(value=doc.id)),
                    ])))
            await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id == doc.id))
            col.index_epoch += 1
            metadata = dict(col.collection_metadata or {})
            for model, key in ((KnowledgeDocument, "document_count"), (KnowledgeChunk, "chunk_count")):
                metadata[key] = (await db.execute(select(func.count(model.id)).where(model.collection_id == col.id))).scalar_one()
            col.collection_metadata = metadata
            await semantic_cache.invalidate_collection(col.id)
        await db.commit()
        print(f"Removed {len(records)} unchanged sample documents. Backup: {backup_path}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    try:
        await clear_samples(parser.parse_args().apply)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
