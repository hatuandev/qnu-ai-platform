"""Compare real migrated tables with ORM, including protection of legacy objects."""

import os

import pytest

if not os.environ.get("TEST_DATABASE_URL"):
    pytest.skip("PostgreSQL test database not configured", allow_module_level=True)

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from qnu.domains.assistants import models as assistant_models  # noqa: F401
from qnu.domains.conversations import models as conversation_models  # noqa: F401
from qnu.domains.integration import models as integration_models  # noqa: F401
from qnu.domains.knowledge import models as knowledge_models  # noqa: F401
from qnu.domains.knowledge.compilation import models as compilation_models  # noqa: F401
from qnu.domains.knowledge.compilation.review import models as review_models  # noqa: F401
from qnu.domains.knowledge.compilation.workflow import models as workflow_models  # noqa: F401
from qnu.domains.knowledge.index import models as index_models  # noqa: F401
from qnu.domains.knowledge.publication import models as publication_models  # noqa: F401
from qnu.domains.lifecycle import models as lifecycle_models  # noqa: F401
from qnu.domains.modelops import models as modelops_models  # noqa: F401
from qnu.domains.ocr import models as ocr_models  # noqa: F401
from qnu.domains.ocr.review import models as ocr_review_models  # noqa: F401
from qnu.domains.operations import models as operations_models  # noqa: F401
from qnu.domains.workspaces import models as workspace_models  # noqa: F401
from qnu.platform.config import get_settings
from qnu.platform.database import Base
from qnu.platform.ownership import include_object


@pytest.mark.asyncio
async def test_migrations_match_models_and_exclude_legacy():
    engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as connection:

        def compare(sync_connection):
            context = MigrationContext.configure(
                sync_connection,
                opts={
                    "compare_type": True,
                    "include_object": include_object,
                    "version_table": "alembic_version_backendv1",
                },
            )
            return compare_metadata(context, Base.metadata)

        difference = await connection.run_sync(compare)
        assert not difference, "\n".join(str(item) for item in difference)
        assert (
            await connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "legacy_head_preserved"
        )
        assert (
            await connection.scalar(text("SELECT version_num FROM alembic_version_backendv1"))
            == "0005_provider_connections"
        )
    await engine.dispose()
