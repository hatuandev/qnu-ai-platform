"""Trust/scope regressions found by the independent session477 review."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.rag.conversation_acts import (
    answer_dialogue_act,
    render_compact,
    resolve_act_scopes,
    summarize_records,
)
from app.modules.rag.schemas import AskResponse
from app.modules.rag.service import RagService
from tests.test_conversation_acts import (
    empty_scopes,
    history_request,
    mock_reload,
    mock_scope_plan,
    mock_snapshot,
    rec,
    resolution,
    snapshot,
)


@pytest.mark.asyncio
async def test_scope_provider_failure_must_not_become_unknown_year_success():
    error = AppException("Model unavailable", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503)
    records = [rec("7100001", "Alpha", [], 1)]
    with (patch("app.modules.rag.conversation_acts.structured_call", AsyncMock(side_effect=error)),
          pytest.raises(AppException) as caught):
        await resolve_act_scopes(AsyncMock(), history_request(), ["toán"], records, {}, snapshot())
    assert caught.value.code == error.code


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["explain", "reformat"])
async def test_explicit_antecedent_year_is_not_lost_when_recomputing(mode):
    antecedent = "Liệt kê các ngành có tổ hợp Toán, Lý, Hóa năm 2025"
    records = [rec("7100001", "Alpha", [2025], 1), rec("7100002", "Beta", [2026], 2),
               rec("7100003", "Gamma", [], 3)]
    with mock_reload(records), mock_snapshot(), mock_scope_plan():
        result = await answer_dialogue_act(AsyncMock(), history_request(previous=antecedent),
            resolution(mode, antecedent_question=antecedent))
    assert result.answer_decision["verified"]["record_count"] == 1
    assert "Beta" not in result.answer and "Gamma" not in result.answer
    assert "Năm 2026:" not in result.answer


def test_compact_unknown_year_records_remain_separate_between_sources():
    records = [rec("7100001", "Alpha", [], 1, "s1"), rec("7100001", "Alpha", [], 2, "s2")]
    scopes = empty_scopes(records)
    answer = render_compact("List", records, scopes, summarize_records(records, scopes))
    assert sum(line.startswith("- 7100001") for line in answer.splitlines()) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["explain", "reformat", "filter"])
async def test_unhandled_act_clarifies_instead_of_replaying_old_listing(mode):
    req = history_request()
    with (patch("app.modules.rag.conversation_resolution.resolve_followup", AsyncMock(return_value=(req, resolution(mode)))),
          patch("app.modules.rag.conversation_acts.answer_dialogue_act", AsyncMock(return_value=None)),
          patch.object(RagService, "_ask", AsyncMock(return_value=AskResponse(status="answered", answer="OLD TABLE"))) as old):
        result = await RagService().ask(AsyncMock(), req)
    assert result.status == "insufficient_context" and result.answer_decision["status"] == "clarify"
    old.assert_not_awaited()
