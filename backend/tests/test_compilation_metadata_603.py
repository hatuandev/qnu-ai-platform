"""Existing metadata endpoint boundary must not import compiler state or decisions."""
import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.services.collection_service import reject_rule_metadata


@pytest.mark.parametrize('payload', [{'version': 1}, {'jobs': {'fake': {'status': 'reviewed'}}}, None])
def test_generic_collection_metadata_cannot_import_compilation_registry(payload):
    with pytest.raises(AppException) as error:
        reject_rule_metadata({'knowledge_compilation_registry': payload})
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_existing_put_handler_rejects_registry_injection_before_any_metadata_write():
    import httpx
    from fastapi import FastAPI

    from app.core.database import get_db
    from app.core.exceptions import register_exception_handlers
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.auth.schemas import AuthActor
    from app.modules.knowledge.models import KnowledgeCollection
    from app.modules.knowledge.router import router
    from tests.test_wiki_snapshot_integration_600 import fixture

    async with fixture() as (factory, cid, _items, _engine):
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router)
        async def database():
            async with factory() as db:
                yield db
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_actor] = lambda: AuthActor(username='fixture603', permissions=['ai.access.admin'])
        async with factory() as db:
            before = (await db.get(KnowledgeCollection, cid)).collection_metadata.copy()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://fixture') as client:
            response = await client.put(f'/knowledge/collections/{cid}', json={'metadata': {
                'knowledge_compilation_registry': {'version': 1, 'jobs': {'fake': {'status': 'reviewed'}}}}})
            assert response.status_code == 403
        async with factory() as db:
            assert (await db.get(KnowledgeCollection, cid)).collection_metadata == before
