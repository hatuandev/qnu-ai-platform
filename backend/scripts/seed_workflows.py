"""Seed Default Workflow Control Plane — Definitions, Drafts, and Immutable Versions."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal
from app.modules.workflows.compiler import workflow_compiler
from app.modules.workflows.models import (
    WorkflowDefinition,
    WorkflowDraft,
    WorkflowVersion,
)
from app.modules.workflows.service import workflow_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_workflows")

WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / "configs" / "workflows"


async def seed_workflow_control_plane() -> int:
    """Read workflow JSON templates, validate them and persist definitions, drafts and published v1.0.0."""
    if not WORKFLOWS_DIR.exists():
        logger.error("Workflow directory not found: %s", WORKFLOWS_DIR)
        return 0

    seeded_count = 0
    async with AsyncSessionLocal() as db:
        for json_file in sorted(WORKFLOWS_DIR.glob("*.json")):
            try:
                raw_data = await asyncio.to_thread(workflow_service._read_json_file, json_file)

                meta = raw_data.get("metadata", {})
                workflow_id = meta.get("name") or json_file.stem.replace(".v1alpha1", "")
                display_name = meta.get("display_name") or workflow_id
                description = meta.get("description") or ""
                module_code = meta.get("module_code") or "general"
                tenant_id = meta.get("scope", {}).get("tenant_id", "tenant_qnu")

                dag_spec = workflow_service._parse_spec_from_json(raw_data)
                validation = workflow_compiler.validate(dag_spec)
                if not validation.is_valid:
                    logger.warning("Workflow %s validation failed: %s", workflow_id, validation.issues)
                    continue

                serialized_spec = workflow_service._serialize_dag_spec(dag_spec)
                content_hash = workflow_service._content_hash(dag_spec)

                # 1. Ensure WorkflowDefinition
                stmt = select(WorkflowDefinition).where(WorkflowDefinition.id == workflow_id)
                res = await db.execute(stmt)
                wf_def = res.scalar_one_or_none()
                if wf_def is None:
                    wf_def = WorkflowDefinition(
                        id=workflow_id,
                        name=workflow_id,
                        display_name=display_name,
                        description=description,
                        module_code=module_code,
                        tenant_id=tenant_id,
                        version="1.0.0",
                        is_active=True,
                        dag_spec=serialized_spec,
                    )
                    db.add(wf_def)
                    await db.flush()
                    logger.info("Created WorkflowDefinition: %s (%s)", workflow_id, display_name)

                # 2. Ensure WorkflowDraft
                draft_stmt = select(WorkflowDraft).where(WorkflowDraft.workflow_id == workflow_id)
                draft_res = await db.execute(draft_stmt)
                draft = draft_res.scalar_one_or_none()
                if draft is None:
                    draft = WorkflowDraft(
                        workflow_id=workflow_id,
                        dag_spec=serialized_spec,
                        revision=1,
                        updated_by="system_seeder",
                    )
                    db.add(draft)
                    await db.flush()
                    logger.info("Created initial WorkflowDraft: %s (revision 1)", workflow_id)

                # 3. Ensure WorkflowVersion v1
                ver_stmt = select(WorkflowVersion).where(
                    WorkflowVersion.workflow_id == workflow_id,
                    WorkflowVersion.version_number == 1,
                )
                ver_res = await db.execute(ver_stmt)
                version = ver_res.scalar_one_or_none()
                if version is None:
                    version = WorkflowVersion(
                        workflow_id=workflow_id,
                        version_number=1,
                        content_hash=content_hash,
                        dag_spec=serialized_spec,
                        validation_report=validation.model_dump(mode="json"),
                        published_by="system_seeder",
                    )
                    db.add(version)
                    await db.flush()
                    logger.info("Published WorkflowVersion: %s v1 (hash: %s...)", workflow_id, content_hash[:8])

                if wf_def.published_version_id != version.id:
                    wf_def.published_version_id = version.id
                    logger.info("Bound published_version_id to WorkflowDefinition: %s", workflow_id)

                seeded_count += 1
            except Exception:
                logger.exception("Failed to seed workflow file %s", json_file.name)

        await db.commit()

    logger.info("Seeding completed successfully: %d workflows ready in Control Plane.", seeded_count)
    return seeded_count


if __name__ == "__main__":
    count = asyncio.run(seed_workflow_control_plane())
    print(f"Total seeded workflows: {count}")
