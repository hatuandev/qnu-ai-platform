import hashlib
from io import BytesIO
from zipfile import ZipFile

import pytest
from docx import Document
from PIL import Image

import tests.test_semantic_lifecycle as lifecycle
from app.core.exceptions import AppException
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import KnowledgeCollection, KnowledgeSourceRevision
from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuQualityFlag,
    QnuSourceInfo,
    QnuStructuredDocument,
)
from app.modules.knowledge.services import source_figure_review as service

storage, database = lifecycle.storage, lifecycle.database


def image_case():
    png = BytesIO()
    Image.new('RGB', (40, 30), '#93abb5').save(png, format='PNG')
    source = Document()
    source.add_picture(BytesIO(png.getvalue()))
    out = BytesIO()
    source.save(out)
    raw = out.getvalue()
    with ZipFile(BytesIO(raw)) as archive:
        image = archive.read(next(n for n in archive.namelist() if n.startswith('word/media/')))
    image_hash = hashlib.sha256(image).hexdigest()
    origin = hashlib.sha256(raw).hexdigest()
    review = {'version': service.VERSION, 'origin_sha256': origin, 'binding_id': 'test-binding',
        'image_sha256': image_hash, 'transcription': 'Node one → Node two',
        'transcription_sha256': hashlib.sha256('Node one → Node two'.encode()).hexdigest(),
        'approval_kind': 'explicit_user_confirmation', 'approval_reference': 'TEST confirmation',
        'recorded_by': 'test-reviewer', 'at': '2026-10-19T00:00:00Z', 'publication_granted': False}
    model = QnuStructuredDocument(title='Independent test image', source=QnuSourceInfo(filename='test.docx', sha256=origin),
        blocks=[QnuBlock(id='figure', type='figure', attributes={'resource': {'sha256': image_hash}},
            quality_flags=[QnuQualityFlag(code='figure_content_unverified', detail='unverified')])])
    return model, raw, review


def test_unapproved_image_stays_blocking():
    model, raw, _ = image_case()
    service.apply_figure_reviews(model, raw, [], 'test-binding')
    assert not model.blocks[0].body
    assert model.blocks[0].quality_flags[0].code == 'figure_content_unverified'


def test_explicit_transcription_keeps_audit_and_does_not_create_relations():
    model, raw, review = image_case()
    service.apply_figure_reviews(model, raw, [review], 'test-binding')
    service.verify_figure_reviews(model, raw, [review], 'test-binding')
    assert model.blocks[0].body == review['transcription']
    assert not model.blocks[0].quality_flags and not model.blocks[0].context_refs
    assert model.blocks[0].attributes['source_figure_review']['publication_granted'] is False


@pytest.mark.parametrize('change', ['source', 'image', 'body', 'binding', 'no_actor', 'no_confirmation'])
def test_invalid_review_fails_closed(change):
    model, raw, review = image_case()
    if change == 'source': review['origin_sha256'] = '0' * 64
    if change == 'image': review['image_sha256'] = '0' * 64
    if change == 'body': review['transcription'] = 'unconfirmed replacement'
    if change == 'binding': review['binding_id'] = 'some-other-binding'
    if change == 'no_actor': review['recorded_by'] = ''
    if change == 'no_confirmation': review['approval_reference'] = ''
    with pytest.raises(AppException):
        service.apply_figure_reviews(model, raw, [review], 'test-binding')
    assert model.blocks[0].quality_flags


def test_receipt_in_markdown_is_not_a_server_record():
    model, raw, review = image_case()
    service.apply_figure_reviews(model, raw, [review], 'test-binding')
    with pytest.raises(AppException):
        service.verify_figure_reviews(model, raw, [], 'test-binding')


def test_body_change_after_review_is_detected():
    model, raw, review = image_case()
    service.apply_figure_reviews(model, raw, [review], 'test-binding')
    model.blocks[0].body = 'unconfirmed replacement'
    with pytest.raises(AppException):
        service.verify_figure_reviews(model, raw, [review], 'test-binding')


async def test_real_db_record_is_authenticated_idempotent_and_queued_only(database, monkeypatch):
    model, raw, review = image_case()
    monkeypatch.setattr(service, 'storage_service', database.storage)
    actor = AuthActor(actor_id='test-reviewer', username='TEST', permissions=['ai.knowledge.update'], authenticated=True)
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        rev.status, rev.origin_file_hash = 'queued', model.source.sha256
        await database.storage.save(rev.snapshot_storage_path, raw)
        await db.commit()
        a = await service.record_figure_review(db, *database.ids, review['image_sha256'], review['transcription'], 'TEST confirmation', actor)
        b = await service.record_figure_review(db, *database.ids, review['image_sha256'], review['transcription'], 'TEST confirmation', actor)
        assert a == b and len(rev.snapshot_metadata[service.KEY]) == 1
        rev.status = 'ready'
        await db.commit()
        with pytest.raises(AppException):
            await service.record_figure_review(db, *database.ids, review['image_sha256'], review['transcription'], 'TEST confirmation', actor)


async def test_cross_collection_cannot_record_confirmation(database, monkeypatch):
    model, raw, review = image_case()
    monkeypatch.setattr(service, 'storage_service', database.storage)
    actor = AuthActor(actor_id='test-reviewer', username='TEST', permissions=['ai.knowledge.update'], authenticated=True)
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        rev.status, rev.origin_file_hash = 'queued', model.source.sha256
        await database.storage.save(rev.snapshot_storage_path, raw)
        other = KnowledgeCollection(name='Other TEST collection', module_code='other-test')
        db.add(other)
        await db.commit()
        with pytest.raises(AppException):
            await service.record_figure_review(db, other.id, *database.ids[1:], review['image_sha256'], review['transcription'], 'TEST confirmation', actor)


async def test_unauthenticated_actor_cannot_record(database):
    actor = AuthActor(actor_id='fake', username='TEST', permissions=['ai.knowledge.update'], authenticated=False)
    async with database.factory() as db:
        with pytest.raises(AppException):
            await service.record_figure_review(db, *database.ids, '0' * 64, 'TEST', 'TEST', actor)
