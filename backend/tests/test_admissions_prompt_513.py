"""Prompt contract checks, not a claim about live model compliance."""

from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.assistants.models import AssistantModel
from app.modules.assistants.runtime import build_runtime_profile
from app.modules.assistants.schemas import AssistantUpdateRequest
from app.modules.assistants.seeder import STANDARD_ASSISTANTS
from app.modules.assistants.services.assistant_lifecycle_service import AssistantLifecycleService


def _template():
    return next(item for item in STANDARD_ASSISTANTS if item["code"] == "admissions")


def test_admissions_prompt_has_no_guarantee_thresholds_or_automatic_export_promise():
    prompt = _template()["system_prompt"]
    for obsolete in ("bảo đảm chắc chắn trúng tuyển", "0.5 - 1.5", ">= 22.5",
                     "hệ thống sẽ tạo tệp tải về", "đề xuất đúng 2 câu hỏi"):
        assert obsolete not in prompt
    for requirement in ("không phải dự báo hay bảo đảm trúng tuyển",
                        "quy tắc được duyệt", "liên kết tải hợp lệ",
                        "Không chèn khối [GỢI Ý]", "không dùng câu trả lời cũ",
                        "không diễn giải thành không có tài liệu"):
        assert requirement in prompt


@pytest.mark.asyncio
async def test_prompt_only_update_preserves_config_and_reaches_runtime():
    template = deepcopy(_template())
    template.pop("config")
    record = AssistantModel(**template, config={"execution_mode": "rag"},
                            tenant_id="tenant_qnu", is_active=True,
                            created_at=datetime(2026, 1, 1, tzinfo=UTC),
                            updated_at=datetime(2026, 1, 1, tzinfo=UTC))
    record.system_prompt = "An existing private custom instruction"
    before = {column.name: deepcopy(getattr(record, column.name))
              for column in AssistantModel.__table__.columns}
    prior_revision = build_runtime_profile(record).assistant_revision
    service = AssistantLifecycleService()
    db = AsyncMock()
    with patch.object(service, "_call_get_record", AsyncMock(return_value=record)):
        result = await service.update_assistant(
            db, "admissions", AssistantUpdateRequest(system_prompt=_template()["system_prompt"]))
    for name, value in before.items():
        if name not in {"system_prompt", "updated_at"}:
            assert getattr(record, name) == value
    runtime = build_runtime_profile(result)
    assert runtime.system_prompt == _template()["system_prompt"]
    assert runtime.assistant_revision != prior_revision
    db.commit.assert_awaited_once()
