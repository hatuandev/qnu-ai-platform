"""Reader route keeps real permission checks and verifies the stored MD/JSON pair."""
import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.database import get_db
from app.core.exceptions import AppException
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuSourceInfo,
    QnuSourceLocation,
    QnuStructuredDocument,
    render_qnu_markdown,
)
from app.modules.knowledge.router import router


@pytest.mark.asyncio
@pytest.mark.parametrize('format', ['reader', 'reader-json'])
@pytest.mark.parametrize('allowed', [False, True])
@pytest.mark.parametrize('corrupt', [False, True])
async def test_reader_route_checks_permission_before_loading_source_pair(format, allowed, corrupt):
    doc = QnuStructuredDocument(title='Fixture', source=QnuSourceInfo(filename='f.docx', sha256='a' * 64),
        blocks=[QnuBlock(id='p', type='text', body='Literal source without transport metadata.', source_locations=[QnuSourceLocation(locator='xml#p1')])])
    md = render_qnu_markdown(doc, document_id='b', revision_id='r').encode()
    js = doc.model_dump_json().encode()
    reference = {'status': 'ready', 'schema_version': doc.schema_version, 'document_id': 'b', 'revision_id': 'r',
        'path': 'snapshot.' + hashlib.sha256(md).hexdigest() + '.qnu-rag-v1.md', 'sha256': hashlib.sha256(md).hexdigest(),
        'structured_path': 'snapshot.' + hashlib.sha256(js).hexdigest() + '.qnu-doc-v1.json', 'structured_sha256': hashlib.sha256(js).hexdigest()}
    revision = KnowledgeSourceRevision(id='r', binding_id='b', origin_file_hash='a' * 64,
        snapshot_storage_path='snapshot', snapshot_metadata={'qnu_markdown': reference})
    db = AsyncMock()
    db.scalars.return_value = SimpleNamespace(one_or_none=lambda: revision)
    actor = AuthActor(username='test-reader', permissions=['ai.knowledge.view'] if allowed else [])
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_actor] = lambda: actor

    @app.exception_handler(AppException)
    async def handle(request, exc):
        return JSONResponse(status_code=exc.status_code, content={'code': exc.code, 'details': getattr(exc, 'details', {})})

    data = {reference['path']: md, reference['structured_path']: js}
    if corrupt:
        data[reference['structured_path']] += b' '
    storage = SimpleNamespace(get=AsyncMock(side_effect=lambda path: data.get(path)))
    resolve = AsyncMock(return_value=reference)
    with patch('app.modules.knowledge.router.source_ingestion_service.get_qnu_markdown_artifact', resolve), patch(
            'app.modules.knowledge.services.qnu_serving.storage_service', storage):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get(f'/knowledge/collections/c/sources/b/revisions/r/qnu-markdown?format={format}')
    assert response.status_code == (409 if corrupt and allowed else 200 if allowed else 403), response.text
    if allowed and not corrupt:
        assert 'Literal source' in response.text
        assert '<!-- rag:block' not in response.text
        assert resolve.await_args.kwargs['collection_id'] == 'c'
        if format == 'reader-json':
            assert response.json()['revision_id'] == 'r' and response.json()['binding_id'] == 'b'
        else:
            assert '.readable.md' in response.headers['content-disposition']
    elif not allowed:
        resolve.assert_not_awaited(); storage.get.assert_not_awaited()
    else:
        assert response.json()['code'] == 'QNU_STANDARD_INVALID'
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_reader_fails_closed_for_missing_revision():
    from app.modules.knowledge.services.source_reader import read_source_document

    db = AsyncMock(); db.scalars.return_value = SimpleNamespace(one_or_none=lambda: None)
    with patch('app.modules.knowledge.services.source_reader.verify_revision_pair', AsyncMock()) as verify:
        with pytest.raises(AppException) as caught:
            await read_source_document(db, 'other-binding', 'other-revision')
        assert caught.value.code == 'SOURCE_REVISION_NOT_FOUND'
        verify.assert_not_awaited()
    parameters = db.scalars.await_args.args[0].compile().params
    assert set(parameters.values()) == {'other-binding', 'other-revision'}
