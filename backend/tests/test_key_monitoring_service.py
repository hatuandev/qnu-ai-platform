from copy import deepcopy
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AppException
from app.modules.modelops.services.key_monitoring_service import key_monitoring_service


def test_preview_orders_available_keys_without_mutating_state() -> None:
    keys = [
        {"id": "3", "name": "Key 3", "priority": 3, "status": "active"},
        {"id": "1", "name": "Key 1", "priority": 1, "status": "active"},
        {"id": "2", "name": "Key 2", "priority": 2, "status": "active"},
        {"id": "busy", "name": "Busy", "priority": 0, "is_leased": True},
        {"id": "off", "name": "Off", "is_active": False},
        {"id": "quota", "name": "Quota", "quota_limit": 10, "usage_tokens": 10},
        {"id": "invalid", "name": "Invalid", "status": "invalid"},
    ]
    before = deepcopy(keys)
    result = key_monitoring_service.preview(keys)
    assert result["dry_run"] is True
    assert result["rotated"] is True
    assert [key["id"] for key in result["key_order"]] == ["1", "2", "3"]
    assert keys == before


def test_preview_recovers_expired_cooldown_but_excludes_pending_cooldown() -> None:
    now = datetime.now(UTC)
    keys = [
        {
            "id": "old",
            "name": "Old",
            "status": "rate_limited",
            "cooldown_until": (now - timedelta(seconds=1)).isoformat(),
        },
        {
            "id": "new",
            "name": "New",
            "status": "rate_limited",
            "cooldown_until": (now + timedelta(minutes=1)).isoformat(),
        },
    ]
    result = key_monitoring_service.preview(keys)
    assert result["rotated"] is False
    assert [key["id"] for key in result["key_order"]] == ["old"]
    assert keys[0]["status"] == "rate_limited"


@pytest.mark.asyncio
async def test_monitoring_rejects_unknown_provider() -> None:
    db = AsyncMock()
    db.get.return_value = None
    with pytest.raises(AppException):
        await key_monitoring_service.history(db, "missing", 30)
    with pytest.raises(AppException):
        await key_monitoring_service.failover_preview(db, "missing")
    db.execute.assert_not_called()
