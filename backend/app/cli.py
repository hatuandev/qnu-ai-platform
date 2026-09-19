"""QNU AI Platform CLI — Database, Migration & Seed Management.

Usage:
    python -m app.cli db check
    python -m app.cli db migrate
    python -m app.cli db seed [--all] [--assistants] [--knowledge] [--workflows] [--document-types] [--model-defaults]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence

from alembic.config import Config
from sqlalchemy import inspect, select, text

from alembic import command
from app.core.config import settings
from app.core.database import AsyncSessionFactory, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("qnu-cli")


def _get_alembic_config() -> Config:
    """Load Alembic configuration pointing to backend/alembic.ini."""
    from pathlib import Path

    alembic_ini_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    alembic_dir = Path(__file__).resolve().parents[1] / "alembic"

    config = Config(str(alembic_ini_path))
    config.set_main_option("script_location", str(alembic_dir))
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    return config


async def check_db_schema() -> bool:
    """Verify database connection, Alembic revision, and presence of core tables."""
    logger.info("Checking database connection and schema integrity...")
    try:
        async with engine.connect() as conn:
            # 1. Test connection
            res = await conn.execute(text("SELECT 1"))
            if res.scalar() != 1:
                logger.error("Database connection test failed.")
                return False
            logger.info("Database connection: OK")

            # 2. Check alembic_version table
            has_alembic = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).has_table("alembic_version")
            )
            if not has_alembic:
                logger.warning("alembic_version table NOT found. Schema has not been initialized via Alembic.")
                return False

            version_res = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            current_rev = version_res.scalar()
            logger.info("Current Alembic revision: %s", current_rev)

            # 3. Check core tables
            tables = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )
            required_tables = {
                "assistants",
                "knowledge_collections",
                "knowledge_documents",
                "workflow_definitions",
                "model_provider_configs",
                "platform_document_types",
            }
            missing = required_tables - tables
            if missing:
                logger.error("Missing required core tables: %s", missing)
                return False
            logger.info("All required core tables are present (%d total tables).", len(tables))

        logger.info("Database schema check: PASSED.")
        return True
    except Exception as exc:
        logger.error("Database check failed with exception: %s", exc)
        return False


def run_db_migrate() -> int:
    """Run alembic upgrade head programmatically."""
    logger.info("Running database migration to HEAD...")
    try:
        config = _get_alembic_config()
        command.upgrade(config, "head")
        logger.info("Database migration to HEAD completed successfully.")
        return 0
    except Exception as exc:
        logger.error("Database migration failed: %s", exc)
        return 1


async def run_db_seed(
    *,
    seed_all: bool = False,
    assistants: bool = False,
    knowledge: bool = False,
    workflows: bool = False,
    document_types: bool = False,
    model_defaults: bool = False,
    ingestion_jobs: bool = False,
) -> int:
    """Execute idempotent database seed operations."""
    if not any([seed_all, assistants, knowledge, workflows, document_types, model_defaults, ingestion_jobs]):
        logger.warning("No seed targets selected. Use --all or specific flags (--assistants, --knowledge, etc.).")
        return 0

    from app.core.storage import storage_service
    from app.modules.assistants.seeder import seed_standard_assistants
    from app.modules.document_types.service import document_types_service
    from app.modules.knowledge.seeder import seed_default_knowledge
    from app.modules.knowledge.service import knowledge_service
    from app.modules.modelops.service import modelops_service
    from app.modules.workflows.service import workflow_service

    logger.info("Ensuring storage bucket...")
    await storage_service.ensure_bucket()

    async with AsyncSessionFactory() as db:
        try:
            if seed_all or document_types:
                logger.info("Syncing document types catalog (ND 30)...")
                await document_types_service.sync_from_catalog(db)
                logger.info("Document types catalog synced.")

            if seed_all or workflows:
                logger.info("Syncing default workflow definitions...")
                await workflow_service.sync_default_workflows(db)
                logger.info("Default workflows synced.")

            if seed_all or assistants:
                logger.info("Seeding standard QNU AI assistants...")
                await seed_standard_assistants(db)
                logger.info("Standard assistants seeded.")

            if seed_all or knowledge:
                logger.info("Seeding default knowledge collections...")
                await seed_default_knowledge(db)
                logger.info("Default knowledge collections seeded.")

            if seed_all or model_defaults:
                logger.info("Initializing system model defaults...")
                await modelops_service.get_system_model_defaults(db)
                logger.info("System model defaults initialized.")

            if seed_all or ingestion_jobs:
                logger.info("Syncing ingestion job records...")
                await knowledge_service.sync_ingestion_job_records(db)
                logger.info("Ingestion job records synced.")

            logger.info("Database seed completed successfully.")
            return 0
        except Exception as exc:
            logger.error("Database seed failed: %s", exc)
            return 1


async def run_knowledge_reconcile(collection_id: str | None = None, auto_fix: bool = False) -> int:
    """Run 4-layer reconciliation across DB, Qdrant, MinIO, and Redis."""
    from app.modules.knowledge.models import KnowledgeCollection
    from app.modules.knowledge.services.reconciliation_service import reconciliation_service

    logger.info("Starting knowledge reconciliation (auto_fix=%s)...", auto_fix)
    async with AsyncSessionFactory() as db:
        if collection_id:
            collections = list(
                (await db.execute(select(KnowledgeCollection).where(KnowledgeCollection.id == collection_id)))
                .scalars()
                .all()
            )
            if not collections:
                logger.error("Collection '%s' not found.", collection_id)
                return 1
        else:
            collections = list((await db.execute(select(KnowledgeCollection))).scalars().all())

        total_issues = 0
        for col in collections:
            logger.info("--- Reconciling Collection: %s ('%s') ---", col.id, col.name)
            report = await reconciliation_service.reconcile_collection(db, col.id)

            logger.info(
                "  DB Docs: %d | DB Chunks: %d | Qdrant Points: %d",
                report["db_documents_count"],
                report["db_chunks_count"],
                report["qdrant_points_count"],
            )

            discrepancies = report.get("discrepancies", [])
            if discrepancies:
                logger.warning("  Found %d discrepancies in collection '%s':", len(discrepancies), col.id)
                for disc in discrepancies:
                    logger.warning("    - [%s] %s", disc.get("type"), disc.get("message"))
                    total_issues += 1
            else:
                logger.info("  Parity status: 100% HEALTHY.")

            if auto_fix and discrepancies:
                logger.info("  Attempting auto-fix for collection '%s'...", col.id)
                # Re-index all approved/ready documents that have missing points or legacy schema
                from app.modules.knowledge.models import KnowledgeDocument
                docs_to_fix = list(
                    (
                        await db.execute(
                            select(KnowledgeDocument).where(
                                KnowledgeDocument.collection_id == col.id,
                                KnowledgeDocument.status.in_(["approved", "ready"]),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                for d in docs_to_fix:
                    logger.info("  Auto-fixing doc %s ('%s')...", d.id, d.title)
                    fix_res = await reconciliation_service.reindex_document(db, d.id)
                    logger.info("  Reindexed doc %s: status=%s, chunks=%d", d.id, fix_res.get("status"), fix_res.get("indexed_chunks", 0))

        if total_issues > 0:
            logger.warning("Reconciliation finished with %d total issue(s).", total_issues)
        else:
            logger.info("All inspected collections are fully synchronized.")
        return 0


async def run_knowledge_reindex(collection_id: str | None = None, document_id: str | None = None) -> int:
    """Run vector re-indexing for a document or all documents in a collection."""
    from app.modules.knowledge.models import KnowledgeDocument
    from app.modules.knowledge.services.reconciliation_service import reconciliation_service

    if not collection_id and not document_id:
        logger.error("Must specify at least --collection-id or --document-id for reindexing.")
        return 1

    async with AsyncSessionFactory() as db:
        if document_id:
            logger.info("Reindexing document %s...", document_id)
            res = await reconciliation_service.reindex_document(db, document_id)
            logger.info("Reindex result: %s", res)
            return 0 if res.get("status") == "ready" else 1

        if collection_id:
            docs = list(
                (
                    await db.execute(
                        select(KnowledgeDocument).where(
                            KnowledgeDocument.collection_id == collection_id,
                            KnowledgeDocument.status.in_(["approved", "ready"]),
                        )
                    )
                )
                .scalars()
                .all()
            )
            logger.info("Reindexing %d document(s) in collection %s...", len(docs), collection_id)
            success = 0
            for d in docs:
                res = await reconciliation_service.reindex_document(db, d.id)
                if res.get("status") == "ready":
                    success += 1
                logger.info("Doc %s ('%s'): %s", d.id, d.title, res.get("message"))
            logger.info("Reindexing completed: %d/%d succeeded.", success, len(docs))
            return 0 if success == len(docs) else 1

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="QNU AI Platform CLI — Database, Migration & Seed Management",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # `db` command group
    db_parser = subparsers.add_parser("db", help="Database management operations")
    db_subparsers = db_parser.add_subparsers(dest="db_action", help="DB actions")

    # `db check`
    db_subparsers.add_parser("check", help="Verify database schema and connection")

    # `db migrate`
    db_subparsers.add_parser("migrate", help="Upgrade schema to Alembic HEAD")

    # `db seed`
    seed_parser = db_subparsers.add_parser("seed", help="Seed initial/idempotent data")
    seed_parser.add_argument("--all", action="store_true", help="Seed all datasets")
    seed_parser.add_argument("--assistants", action="store_true", help="Seed standard assistants")
    seed_parser.add_argument("--knowledge", action="store_true", help="Seed default knowledge")
    seed_parser.add_argument("--workflows", action="store_true", help="Sync default workflows")
    seed_parser.add_argument("--document-types", action="store_true", help="Sync ND 30 document types")
    seed_parser.add_argument("--model-defaults", action="store_true", help="Init system model defaults")
    seed_parser.add_argument("--ingestion-jobs", action="store_true", help="Sync ingestion jobs")

    # `knowledge` command group
    kn_parser = subparsers.add_parser("knowledge", help="Knowledge base reconciliation & reindexing")
    kn_subparsers = kn_parser.add_subparsers(dest="kn_action", help="Knowledge actions")

    # `knowledge reconcile`
    kn_rec_parser = kn_subparsers.add_parser("reconcile", help="Audit 4-layer parity (DB, Qdrant, MinIO, Redis)")
    kn_rec_parser.add_argument("--collection-id", help="Target collection ID (default: all)")
    kn_rec_parser.add_argument("--fix", action="store_true", help="Auto-reindex documents with parity discrepancies")

    # `knowledge reindex`
    kn_reindex_parser = kn_subparsers.add_parser("reindex", help="Reindex vectors in Qdrant")
    kn_reindex_parser.add_argument("--collection-id", help="Collection ID to reindex")
    kn_reindex_parser.add_argument("--document-id", help="Specific Document ID to reindex")

    # `secrets` command group
    sec_parser = subparsers.add_parser("secrets", help="Provider API keys and secrets encryption management")
    sec_subparsers = sec_parser.add_subparsers(dest="sec_action", help="Secrets actions")

    # `secrets check`
    sec_subparsers.add_parser("check", help="Inspect secrets and report encryption status (read-only)")

    # `secrets migrate`
    sec_migrate_parser = sec_subparsers.add_parser("migrate", help="Run secrets migration")
    sec_migrate_group = sec_migrate_parser.add_mutually_exclusive_group(required=True)
    sec_migrate_group.add_argument("--dry-run", action="store_true", help="Audit mode without changes")
    sec_migrate_group.add_argument("--apply", action="store_true", help="Encrypt plaintext secrets in DB")
    sec_migrate_group.add_argument("--verify", action="store_true", help="Verify 100% encrypted & decryptable")

    args = parser.parse_args(argv)

    if args.command == "db":
        if args.db_action == "check":
            passed = asyncio.run(check_db_schema())
            return 0 if passed else 1
        if args.db_action == "migrate":
            return run_db_migrate()
        if args.db_action == "seed":
            return asyncio.run(
                run_db_seed(
                    seed_all=args.all,
                    assistants=args.assistants,
                    knowledge=args.knowledge,
                    workflows=args.workflows,
                    document_types=args.document_types,
                    model_defaults=args.model_defaults,
                    ingestion_jobs=args.ingestion_jobs,
                )
            )
        db_parser.print_help()
        return 1

    if args.command == "knowledge":
        if args.kn_action == "reconcile":
            return asyncio.run(run_knowledge_reconcile(collection_id=args.collection_id, auto_fix=args.fix))
        if args.kn_action == "reindex":
            return asyncio.run(run_knowledge_reindex(collection_id=args.collection_id, document_id=args.document_id))
        kn_parser.print_help()
        return 1

    if args.command == "secrets":
        import scripts.migrate_provider_secrets as migrator
        if args.sec_action == "check":
            return asyncio.run(migrator.run_dry_run())
        if args.sec_action == "migrate":
            if args.dry_run:
                return asyncio.run(migrator.run_dry_run())
            if args.apply:
                return asyncio.run(migrator.run_apply())
            if args.verify:
                return asyncio.run(migrator.run_verify())
        sec_parser.print_help()
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
