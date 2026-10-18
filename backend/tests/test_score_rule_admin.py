"""Approval transitions and permissions must precede active calculator use."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppException
from app.modules.knowledge.score_rule_schemas import RuleAction, RuleDraft
from app.modules.knowledge.services import score_rule_service as service
from tests.test_score_conversion import percentile_rule


def definition():
    rule, _ = percentile_rule((("100", "10"), ("200", "20")))
    return {**rule.model_dump(mode="json", exclude={"status", "reviewed_by", "reviewed_at"}), "id": "conversion"}


def actor(allowed=True):
    return SimpleNamespace(actor_id="operator", has_permission=lambda _: allowed)


def action(kind, version, key="request-123"):
    return RuleAction(action=kind, expected_version=version, request_id=key,
                      reason="Đã đối chiếu văn bản chính thức", confirmed=True)


@pytest.mark.asyncio
async def test_draft_approve_activate_revoke_and_idempotency():
    col = SimpleNamespace(id="cc", collection_metadata={})
    db = AsyncMock()
    with patch.object(service, "load_collection", AsyncMock(return_value=col)), \
         patch.object(service, "validate_definition", AsyncMock()):
        draft = RuleDraft(definition=definition(), expected_version=0, request_id="draft-request")
        result = await service.create_draft(db, actor(), "cc", draft)
        assert result.version == 1 and result.items[0].status == "draft"
        result = await service.transition(db, actor(), "cc", "conversion", action("approve", 1))
        assert result.items[0].reviewed_by == "operator"
        assert result.items[0].status == "approved"
        result = await service.transition(db, actor(), "cc", "conversion", action("activate", 2, "activate-request"))
        assert result.items[0].status == "active"
        again = await service.transition(db, actor(), "cc", "conversion", action("activate", 2, "activate-request"))
        assert again.version == result.version and len(again.audit) == 3
        result = await service.transition(db, actor(), "cc", "conversion", action("revoke", 3, "revoke-request"))
        assert result.items[0].status == "revoked" and len(result.audit) == 4
        assert service.active_rules(col.collection_metadata) == []


@pytest.mark.asyncio
async def test_draft_cannot_activate_and_stale_version_rejected():
    col = SimpleNamespace(id="cc", collection_metadata={})
    with patch.object(service, "load_collection", AsyncMock(return_value=col)):
        await service.create_draft(AsyncMock(), actor(), "cc", RuleDraft(
            definition=definition(), expected_version=0, request_id="draft-request"))
        for payload, code in [(action("activate", 1), "SCORE_RULE_TRANSITION_INVALID"),
                              (action("approve", 0), "SCORE_RULE_VERSION_CONFLICT")]:
            with pytest.raises(AppException) as caught:
                await service.transition(AsyncMock(), actor(), "cc", "conversion", payload)
            assert caught.value.code == code


@pytest.mark.asyncio
async def test_permission_denied_before_database_access():
    db = AsyncMock()
    with pytest.raises(AppException) as caught:
        await service.transition(db, actor(False), "cc", "conversion", action("approve", 1))
    assert caught.value.status_code == 403
    db.execute.assert_not_called()


def test_client_cannot_supply_reviewer_or_bypass_confirmation():
    with pytest.raises(ValidationError):
        RuleDraft(definition={**definition(), "reviewed_by": "fake"},
                  expected_version=0, request_id="draft-request")
    with pytest.raises(ValidationError):
        action("approve", 1).model_validate({**action("approve", 1).model_dump(), "confirmed": False})


def test_legacy_verified_json_is_not_activation_authority():
    assert service.active_rules({"score_conversion_rules": [{"status": "verified"}]}) == []


def test_unicode_rule_ids_are_supported_without_path_separators():
    from app.modules.rag.score_conversion_schemas import ConversionDefinition

    assert ConversionDefinition.model_validate({**definition(), "id": "qnu-2026-ĐNL-A01-THPT"}).id.endswith("THPT")
    with pytest.raises(ValidationError):
        ConversionDefinition.model_validate({**definition(), "id": "invalid/path"})


def test_generic_metadata_api_cannot_bypass_review():
    from app.modules.knowledge.services.collection_service import reject_rule_metadata

    for key in service.PROTECTED_KEYS:
        with pytest.raises(AppException) as caught:
            reject_rule_metadata({key: {"items": [{"status": "active"}]}})
        assert caught.value.status_code == 403


@pytest.mark.asyncio
async def test_failed_evidence_validation_cannot_approve_or_write_audit():
    col = SimpleNamespace(id="cc", collection_metadata={})
    db = AsyncMock()
    with patch.object(service, "load_collection", AsyncMock(return_value=col)):
        await service.create_draft(db, actor(), "cc", RuleDraft(
            definition=definition(), expected_version=0, request_id="draft-request"))
        before = col.collection_metadata
        db.flush.reset_mock()
        with (patch.object(service, "validate_definition", AsyncMock(side_effect=AppException("Stale", code="SCORE_RULE_STALE", status_code=409))),
              pytest.raises(AppException)):
            await service.transition(db, actor(), "cc", "conversion", action("approve", 1))
        assert col.collection_metadata == before
        db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_conflicting_activation_rejected_but_deactivation_permitted():
    col = SimpleNamespace(id="cc", collection_metadata={})
    db = AsyncMock()
    with (patch.object(service, "load_collection", AsyncMock(return_value=col)),
          patch.object(service, "validate_definition", AsyncMock())):
        for rule_id in ["one", "two"]:
            version = service.registry(col.collection_metadata).version
            await service.create_draft(db, actor(), "cc", RuleDraft(
                definition={**definition(), "id": rule_id}, expected_version=version, request_id=f"draft-{rule_id}"))
            await service.transition(db, actor(), "cc", rule_id, action("approve", version + 1, f"approve-{rule_id}"))
        result = await service.transition(db, actor(), "cc", "one", action("activate", 4, "activate-one"))
        assert len(service.active_rules(col.collection_metadata)) == 1
        with pytest.raises(AppException) as caught:
            await service.transition(db, actor(), "cc", "two", action("activate", result.version, "activate-two"))
        assert caught.value.code == "SCORE_RULE_OVERLAP"
        await service.transition(db, actor(), "cc", "one", action("deactivate", 5, "deactivate-one"))
        assert service.active_rules(col.collection_metadata) == []


@pytest.mark.asyncio
async def test_preview_validates_current_cells_without_writes_or_approval():
    from app.modules.knowledge.score_rule_schemas import RulePreview
    from tests.test_score_conversion import snapshot

    rule, blocks = percentile_rule((("100", "10"), ("200", "20")))
    col = SimpleNamespace(id="cc", collection_metadata={})
    db = AsyncMock()
    with patch.object(service, "load_collection", AsyncMock(return_value=col)):
        await service.create_draft(db, actor(), "cc", RuleDraft(
            definition=definition(), expected_version=0, request_id="draft-request"))
        db.flush.reset_mock()
        before = col.collection_metadata
        with (patch("app.modules.rag.retriever.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snapshot())),
              patch("app.modules.rag.score_conversion.load_rule_blocks", AsyncMock(return_value=blocks))):
            result = await service.preview(db, actor(), "cc", "conversion", RulePreview(
                expected_version=1, combination=rule.mappings[0].combination, score="150"))
        assert result.result == "15.00" and result.is_preview is True
        assert col.collection_metadata == before
        assert service.registry(before).items[0].reviewed_by is None
        db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_reused_request_id_with_different_command_rejected():
    col = SimpleNamespace(id="cc", collection_metadata={})
    with patch.object(service, "load_collection", AsyncMock(return_value=col)):
        await service.create_draft(AsyncMock(), actor(), "cc", RuleDraft(
            definition=definition(), expected_version=0, request_id="same-request"))
        with pytest.raises(AppException) as caught:
            await service.transition(AsyncMock(), actor(), "cc", "conversion", action("approve", 1, "same-request"))
        assert caught.value.code == "SCORE_RULE_IDEMPOTENCY_CONFLICT"


@pytest.mark.asyncio
async def test_http_review_permission_and_payload_boundary():
    import httpx
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    from app.core.database import get_db
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.auth.schemas import AuthActor
    from app.modules.knowledge.score_rule_router import router

    app = FastAPI()
    app.include_router(router)
    current = AuthActor(username="writer", actor_id="writer", permissions=["ai.knowledge.update", "ai.knowledge.view"])
    app.dependency_overrides[get_current_actor] = lambda: current
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    @app.exception_handler(AppException)
    async def handle_error(request, exc):
        return JSONResponse({"code": exc.code}, status_code=exc.status_code)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        with patch.object(service, "transition", AsyncMock()) as call:
            denied = await client.post("/collections/cc/score-rules/conversion/actions", json=action("approve", 1).model_dump())
            assert denied.status_code == 403
            call.assert_not_awaited()
        forged = await client.post("/collections/cc/score-rules", json={
            "definition": {**definition(), "reviewed_by": "fake"}, "expected_version": 0, "request_id": "fake-request"})
        assert forged.status_code == 422
        current.permissions.append("ai.knowledge.review")
        with patch.object(service, "transition", AsyncMock(return_value=service.RuleRegistry())) as call:
            accepted = await client.post("/collections/cc/score-rules/conversion/actions", json=action("approve", 1).model_dump())
            assert accepted.status_code == 200
            assert call.await_args.args[1].actor_id == "writer"


@pytest.mark.asyncio
async def test_import_drafts_is_idempotent_and_never_approved():
    from app.modules.knowledge.score_rule_schemas import RuleImport

    col = SimpleNamespace(id="cc", collection_metadata={})
    command = RuleImport(definitions=[{**definition(), "id": "one"}, {**definition(), "id": "two"}],
                         expected_version=0, request_id="x" * 100)
    with patch.object(service, "load_collection", AsyncMock(return_value=col)):
        result = await service.import_drafts(AsyncMock(), actor(), "cc", command)
        assert result.version == 2 and all(item.status == "draft" for item in result.items)
        again = await service.import_drafts(AsyncMock(), actor(), "cc", command)
        assert again.version == 2 and len(again.audit) == 2
