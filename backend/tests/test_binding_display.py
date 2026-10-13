"""Pending display snapshots must never activate an unreviewed revision."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.knowledge.models import KnowledgeBinding
from app.modules.knowledge.services.binding_display import (
    load_binding_display_metadata,
    resolve_binding_display_metadata,
)
from app.modules.knowledge.services.binding_service import BindingService


@pytest.mark.asyncio
async def test_pending_revision_title_is_used_without_changing_active_pointer():
    binding = KnowledgeBinding(id="bnd_pending", collection_id="col", repository_document_id="doc", tenant_id="tenant")
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(all=lambda: [(binding, None)])
    snapshot = {binding.id: {"title": "Tài liệu cần duyệt", "file_name": "tài liệu.pdf"}}
    with patch("app.modules.knowledge.services.binding_service.get_scoped_collection", AsyncMock(return_value=SimpleNamespace(tenant_id="tenant", workspace_id=None))), patch("app.modules.knowledge.services.binding_service.load_binding_display_metadata", AsyncMock(return_value=snapshot)):
        items = await BindingService().list_bindings(db, "col")
    assert items[0].document_title == "Tài liệu cần duyệt"
    assert items[0].file_name == "tài liệu.pdf"
    assert items[0].active_source_revision_id is None
    assert items[0].source_status is None
    assert binding.active_source_revision_id is None


@pytest.mark.asyncio
async def test_no_revision_uses_import_snapshot_without_repository_dependency():
    binding = KnowledgeBinding(id="pending", collection_id="col", repository_document_id="doc", tenant_id="tenant")
    item = SimpleNamespace(knowledge_binding_id="pending", origin_title="Đang xử lý", origin_file_name="original.docx")
    db = AsyncMock()
    db.execute.side_effect = [SimpleNamespace(all=list), SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [item]))]
    result = await load_binding_display_metadata(db, [binding])
    assert result["pending"] == {"title": "Đang xử lý", "file_name": "original.docx"}
    assert db.execute.await_count == 2


def test_empty_draft_metadata_does_not_erase_active_filename():
    assert resolve_binding_display_metadata({"title": "Old", "file_name": "original.pdf"}, {"title": "New", "file_name": None}) == {"title": "New", "file_name": "original.pdf"}


@pytest.mark.asyncio
async def test_detail_uses_pending_title_without_promoting_revision():
    binding = KnowledgeBinding(id="detail", collection_id="col", repository_document_id="doc", tenant_id="tenant")
    db = AsyncMock()
    with patch("app.modules.knowledge.services.binding_service.get_scoped_binding", AsyncMock(return_value=binding)), patch("app.modules.knowledge.services.binding_service.load_binding_display_metadata", AsyncMock(return_value={"detail": {"title": "Nguồn chờ duyệt", "file_name": "source.pdf"}})):
        result = await BindingService().get_binding(db, "detail")
    assert result.document_title == "Nguồn chờ duyệt"
    assert result.file_name == "source.pdf"
    assert result.active_source_revision_id is None
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_binding_list_performs_no_queries():
    db = AsyncMock()
    assert await load_binding_display_metadata(db, []) == {}
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_database_error_is_not_replaced_with_fake_names():
    db = AsyncMock()
    db.execute.side_effect = ConnectionError("Database unavailable")
    with pytest.raises(ConnectionError):
        await load_binding_display_metadata(db, [SimpleNamespace(id="binding")])
