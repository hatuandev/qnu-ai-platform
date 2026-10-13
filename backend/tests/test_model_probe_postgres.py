"""Real PostgreSQL CRUD and observation merges, isolated by an outer rollback."""

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.schemas import (
    ModelCapabilityConfig,
    ProviderConfigCreate,
    ProviderConfigUpdate,
)
from app.modules.modelops.services.chat_capabilities import save_chat_capabilities
from app.modules.modelops.services.provider_service import ProviderService

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv("QNU_TEST_MODELOPS_DB") != "1", reason="Opt-in PostgreSQL rollback fixture"
    ),
]


async def test_model_role_roundtrip_primary_removal_and_merge():
    engine = create_async_engine(settings.DATABASE_URL)
    tag = uuid.uuid4().hex[:8]
    try:
        async with engine.connect() as conn:
            outer = await conn.begin()
            try:
                async with AsyncSession(
                    bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
                ) as db:
                    service = ProviderService()
                    created = await service.create_provider(
                        db,
                        ProviderConfigCreate(
                            name=f"probe-{tag}",
                            provider_type="custom",
                            api_base_url="http://fixture/api",
                            models=["opaque-a", "opaque-b"],
                        ),
                    )
                    provider_id = created["id"]
                    updated = await service.update_provider(
                        db,
                        provider_id,
                        ProviderConfigUpdate(
                            models=["opaque-b"],
                            model_capabilities={
                                "opaque-b": ModelCapabilityConfig(probe_role="reranker")
                            },
                        ),
                    )
                    assert updated["model_name"] == "opaque-b"
                    assert updated["model_capabilities"]["opaque-b"]["probe_role"] == "reranker"
                    await service.update_provider(
                        db,
                        provider_id,
                        ProviderConfigUpdate(
                            model_capabilities={
                                "opaque-b": ModelCapabilityConfig(
                                    probe_role="embedding", embedding_dimension=17
                                )
                            }
                        ),
                    )
                    from app.modules.modelops.services.model_catalog_service import (
                        model_catalog_service,
                    )

                    assert (
                        await model_catalog_service.resolve_embedding_dimension(
                            db, provider_id=provider_id, model_name="opaque-b"
                        )
                        == 17
                    )
                    await save_chat_capabilities(
                        db,
                        provider_id,
                        "opaque-b",
                        "http://fixture/api",
                        {"temperature_supported": False},
                    )
                    row = (
                        await db.execute(
                            select(ModelProviderConfig)
                            .where(ModelProviderConfig.id == provider_id)
                            .execution_options(populate_existing=True)
                        )
                    ).scalar_one()
                    assert (
                        row.extra_config["model_capabilities"]["opaque-b"]["probe_role"]
                        == "embedding"
                    )
                    assert "opaque-a" not in row.extra_config["models"]
                    empty = await service.update_provider(
                        db, provider_id, ProviderConfigUpdate(models=[])
                    )
                    assert empty["models"] == [] and empty["model_name"] is None
            finally:
                await outer.rollback()
        async with engine.connect() as conn:
            assert (
                await conn.execute(
                    select(ModelProviderConfig.id).where(ModelProviderConfig.name == f"probe-{tag}")
                )
            ).first() is None
    finally:
        await engine.dispose()
