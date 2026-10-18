"""Regression contracts for provider routing and workflow terminal audit."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.modules.modelops.schemas import LLMGenerateRequest
from app.modules.workflows.schemas import WorkflowDagSpec, WorkflowExecuteRequest
from app.modules.workflows.service import workflow_service


def test_chat_routes_do_not_send_proxy_alias_to_embedding_server():
    from app.modules.modelops.services.chat_routes import plan_chat_routes

    providers = [
        {"id": "ai", "models": ["encoder"], "model_specs": {"encoder": {"type": "embedding"}}},
        {"id": "proxy", "models": ["vendor/alias[1m]"]},
        {"id": "backup", "models": ["backup-chat"]},
    ]
    request = LLMGenerateRequest(messages=[{"role": "user", "content": "hello"}], preferred_model_name="vendor/alias[1m]",
                                 fallback_model_name="backup-chat")
    assert [(p["id"], m) for p, m in plan_chat_routes(providers, request)] == [
        ("proxy", "vendor/alias[1m]"), ("backup", "backup-chat")]


def test_chat_routes_keep_two_models_on_same_explicit_provider():
    from app.modules.modelops.services.chat_routes import plan_chat_routes

    request = LLMGenerateRequest(messages=[{"role": "user", "content": "hello"}], preferred_provider_id="proxy",
                                 preferred_model_name="first", fallback_provider_id="proxy",
                                 fallback_model_name="second")
    assert [m for _, m in plan_chat_routes([{"id": "proxy", "models": []}], request)] == ["first", "second"]


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [RuntimeError("engine setup failed"), asyncio.CancelledError(), TimeoutError()])
async def test_workflow_boundary_finalizes_failure_after_rollback(error):
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
    spec = WorkflowDagSpec(entry_node_id="in", nodes=[])
    with (patch.object(workflow_service, "get_workflow_spec", AsyncMock(return_value=spec)),
          patch("app.modules.workflows.service.dag_engine.execute", AsyncMock(side_effect=error)),
          patch("app.modules.workflows.service.persist_boundary_failure", AsyncMock()) as audit,
          pytest.raises(type(error))):
        await workflow_service.execute(db, WorkflowExecuteRequest(workflow_id="wf", inputs={}))
    db.rollback.assert_awaited()
    audit.assert_awaited_once()
    assert audit.call_args.args[1] == ("cancelled" if isinstance(error, asyncio.CancelledError) else "failed")


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["setup", "finalize", "rollback"])
async def test_workflow_boundary_covers_persistence_failures(stage):
    from app.modules.workflows.schemas import WorkflowExecuteResponse

    db = AsyncMock()
    db.add = MagicMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
    if stage == "setup":
        db.flush.side_effect = RuntimeError("setup failed")
    elif stage == "finalize":
        db.commit.side_effect = [None, RuntimeError("finalize failed")]
    else:
        db.rollback.side_effect = RuntimeError("rollback failed")
    spec = WorkflowDagSpec(entry_node_id="in", nodes=[])
    result = WorkflowExecuteResponse(execution_id="unused", workflow_id="wf", status="completed")
    with (patch.object(workflow_service, "get_workflow_spec", AsyncMock(return_value=spec)),
          patch("app.modules.workflows.service.dag_engine.execute", AsyncMock(
              return_value=result, side_effect=RuntimeError("engine failed") if stage == "rollback" else None)),
          patch("app.modules.workflows.service.persist_boundary_failure", AsyncMock()) as audit,
          pytest.raises(RuntimeError)):
        await workflow_service.execute(db, WorkflowExecuteRequest(workflow_id="wf", inputs={}))
    audit.assert_awaited_once()
    assert audit.call_args.args[3] == ("engine" if stage == "rollback" else stage)


@pytest.mark.asyncio
async def test_readiness_fails_closed_on_db_outage_and_tenant_mismatch():
    from types import SimpleNamespace

    from app.modules.assistants.readiness import readiness_engine

    db = AsyncMock()
    db.get.side_effect = RuntimeError("database unavailable")
    assert (await readiness_engine._check_knowledge(db, "col", "tenant"))[1]
    db.get.side_effect = None
    db.get.return_value = SimpleNamespace(tenant_id="other-tenant")
    assert (await readiness_engine._check_knowledge(db, "col", "tenant"))[1]


@pytest.mark.asyncio
async def test_model_readiness_exposes_missing_credentials_and_wrong_role():
    from types import SimpleNamespace

    from app.modules.assistants.model_readiness import check_model_routes
    from app.modules.assistants.schemas import AssistantLifecycleConfig

    provider = SimpleNamespace(id="ai", provider_type="custom", model_name="opaque", api_key_encrypted=None,
                               extra_config={"models": ["opaque"], "model_specs": {"opaque": {"type": "embedding"}}})
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [provider]
    keys = MagicMock()
    keys.scalars.return_value.all.return_value = []
    db.execute.side_effect = [result, keys]
    config = AssistantLifecycleConfig(model_policy={"preferred_provider_id": "ai", "primary_model": "opaque"},
                                      knowledge_policy={"reranker_policy": {"enabled": False}})
    errors = await check_model_routes(db, config)
    assert len(errors) == 2
    assert any("vai trò" in error for error in errors)
    assert any("khóa API" in error for error in errors)


@pytest.mark.asyncio
async def test_readiness_managed_disabled_keys_do_not_fall_back_to_stale_json_key():
    from types import SimpleNamespace

    from app.modules.assistants.model_readiness import check_model_routes
    from app.modules.assistants.schemas import AssistantLifecycleConfig

    provider = SimpleNamespace(id="proxy", provider_type="custom", model_name="alias",
                               api_key_encrypted="old-key", extra_config={"models": ["alias"]})
    key = SimpleNamespace(provider_id="proxy", is_active=False, status="invalid")
    results = [MagicMock(), MagicMock()]
    results[0].scalars.return_value.all.return_value = [provider]
    results[1].scalars.return_value.all.return_value = [key]
    db = AsyncMock()
    db.execute.side_effect = results
    config = AssistantLifecycleConfig(model_policy={"preferred_provider_id": "proxy", "primary_model": "alias"},
                                      knowledge_policy={"reranker_policy": {"enabled": False}})
    assert any("khóa API" in e for e in await check_model_routes(db, config))


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
async def test_real_adapter_failover_only_calls_configured_chat_routes(monkeypatch, stream):
    from types import SimpleNamespace

    from app.modules.modelops.services.inference_service import InferenceService

    calls = []
    def upstream(request):
        payload = json.loads(request.content)
        calls.append((request.url.host, payload["model"]))
        if request.url.host == "fixture-router":
            return httpx.Response(503, json={"error": {"message": "temporary unavailable"}})
        assert request.url.host == "fixture-backup"
        if stream:
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=
                'data: {"model":"served-backup","choices":[{"delta":{"content":"OK"},"finish_reason":null}]}\n\n'
                'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}\n\n'
                'data: [DONE]\n\n')
        return httpx.Response(200, json={"model": "served-backup", "choices": [
            {"message": {"content": "OK"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(upstream)))
    providers = [{"id": pid, "name": f"{pid}-{stream}", "provider_type": "custom", "models": [model],
                  "model_name": model, "api_key": "real-fixture-key", "api_base_url": f"http://{pid}/v1",
                  "timeout_seconds": 10} for pid, model in [
                      ("fixture-ai", "opaque-encoder"), ("fixture-router", "alias[1m]"), ("fixture-backup", "backup-alias")]]
    providers[0]["model_specs"] = {"opaque-encoder": {"type": "embedding"}}
    facade = SimpleNamespace(check_quota_available=AsyncMock(), get_active_providers=AsyncMock(return_value=providers),
                             record_usage_log=AsyncMock())
    service = InferenceService(facade)
    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
    request = LLMGenerateRequest(messages=[{"role": "user", "content": "hello"}],
        preferred_provider_id="fixture-router", preferred_model_name="alias[1m]",
        fallback_provider_id="fixture-backup", fallback_model_name="backup-alias")
    with patch("app.modules.modelops.services.inference_service.provider_key_rotation_service.acquire",
               AsyncMock(return_value=SimpleNamespace(managed=False, lease=None))):
        if stream:
            assert "".join([chunk async for chunk in service.generate_stream(db, request)]) == "OK"
        else:
            result = await service.generate(db, request)
            assert result.provider_id == "fixture-backup" and result.is_fallback
    # One bounded transient retry on the configured primary, then only its
    # configured backup. No embedding/default model may enter the cascade.
    assert calls == [("fixture-router", "alias[1m]"), ("fixture-router", "alias[1m]"),
                     ("fixture-backup", "backup-alias")]
    assert facade.record_usage_log.call_args.kwargs["model_name"] == "served-backup"
