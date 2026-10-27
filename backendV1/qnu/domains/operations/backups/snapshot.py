"""Freeze workspace metadata and blob references; omit all global provider/key tables."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.platform.database import Base
from qnu.platform.errors import Conflict, PayloadTooLarge
from qnu.platform.ownership import V1_TABLES

CHILDREN = {
    "ocr_run_artifacts": ("ocr_processing_runs", "run_id"),
    "ocr_run_pages": ("ocr_processing_runs", "run_id"),
    "kb_compilation_artifacts": ("kb_compilation_runs", "run_id"),
    "kb_compilation_review_artifacts": ("kb_compilation_reviews", "review_id"),
}


async def freeze(db: AsyncSession, workspace_id: str) -> tuple[dict, dict[str, str | None]]:
    tables = {}
    for name in sorted(V1_TABLES):
        table = Base.metadata.tables.get(name)
        if table is None or name.startswith("ops_"):
            continue
        if "workspace_id" in table.c:
            statement = select(table).where(table.c.workspace_id == workspace_id)
        elif name == "workspaces":
            statement = select(table).where(table.c.id == workspace_id)
        elif name in CHILDREN:
            parent_name, fk = CHILDREN[name]
            parent = Base.metadata.tables[parent_name]
            statement = (
                select(table)
                .join(parent, table.c[fk] == parent.c.id)
                .where(parent.c.workspace_id == workspace_id)
            )
        else:
            continue
        values = [
            dict(row)
            for row in (
                await db.execute(statement.order_by(*table.primary_key.columns).limit(100001))
            ).mappings()
        ]
        if len(values) > 100000:
            raise PayloadTooLarge(
                "Snapshot vượt giới hạn số bản ghi.", code="backup_limit_exceeded"
            )
        tables[name] = json.loads(json.dumps(values, default=str, ensure_ascii=False))
    references = {}

    def reference(key: str, expected: str | None) -> None:
        if not key.startswith(
            (
                f"v1/workspaces/{workspace_id}/",
                f"ocr-spelling/{workspace_id}/",
                f"ocr-text/{workspace_id}/",
            )
        ):
            raise Conflict("Tệp nằm ngoài workspace sao lưu.", code="backup_source_scope_invalid")
        if key in references and references[key] != expected:
            raise Conflict(
                "Hash tham chiếu nguồn mâu thuẫn.", code="backup_source_integrity_failed"
            )
        references[key] = expected

    for name, rows in tables.items():
        for row in rows:
            if name == "kb_source_revisions":
                reference(row["storage_key"], row["sha256"])
            if name in {
                "ocr_run_artifacts",
                "kb_compilation_artifacts",
                "kb_compilation_review_artifacts",
            }:
                reference(row["blob_key"], row["sha256"])
            if name == "ocr_text_versions":
                reference(row["document_key"], row["canonical_sha256"])
                reference(row["markdown_key"], row["markdown_sha256"])
            if name == "kb_index_runs":
                if row["manifest_key"]:
                    reference(row["manifest_key"], row["manifest_sha256"])
                for receipt in row["batch_receipts"]:
                    reference(receipt["raw_key"], receipt["raw_sha256"])
            if name == "ocr_spelling_runs":
                reference(f"ocr-spelling/{workspace_id}/{row['id']}/raw-response", None)
    return {
        "schema_version": "qnu.workspace-evidence-snapshot/v1",
        "workspace_id": workspace_id,
        "tables": tables,
    }, references
