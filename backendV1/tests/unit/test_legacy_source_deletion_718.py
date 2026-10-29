"""Legacy tombstones need a new confirmed purge; never bypass content uniqueness."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.sources.service import source_service
from qnu.domains.lifecycle.targets import require_operation
from qnu.platform.errors import Conflict


def test_deleted_source_can_request_new_permanent_preview_but_other_deletes_stay_blocked():
    deleted = SimpleNamespace(status="deleted")
    require_operation("source", "delete", SimpleNamespace(), deleted)
    for kind in ("collection", "document", "assistant"):
        with pytest.raises(Conflict) as caught:
            require_operation(kind, "delete", SimpleNamespace(), deleted)
        assert caught.value.code == "lifecycle_transition_invalid"


@pytest.mark.asyncio
async def test_duplicate_legacy_tombstone_has_actionable_message_without_internal_id():
    db = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(status="deleted")),
        scalar=AsyncMock(return_value=None),
    )
    error = await source_service._duplicate_error(db, "w", "internal-source-id", None)
    assert error.code == "duplicate_content_deleted"
    assert "Hoàn tất xóa" in error.detail
    assert "internal-source-id" not in error.detail


@pytest.mark.asyncio
async def test_pending_purge_duplicate_does_not_offer_another_delete():
    db = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(status="deleted")),
        scalar=AsyncMock(return_value="accepted-action"),
    )
    error = await source_service._duplicate_error(db, "w", "source", None)
    assert error.code == "source_purge_pending"


@pytest.mark.asyncio
async def test_regular_duplicate_still_blocks_and_same_source_revision_is_unchanged():
    db = SimpleNamespace(get=AsyncMock(return_value=None), scalar=AsyncMock())
    assert (
        await source_service._duplicate_error(db, "w", "source", None)
    ).code == "duplicate_content"
    assert (
        await source_service._duplicate_error(db, "w", "source", "source")
    ).code == "revision_unchanged"
    db.get.assert_awaited_once()
    db.scalar.assert_not_awaited()
