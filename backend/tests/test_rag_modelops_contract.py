"""Scope, policy and error contracts shared by RAG and workflow runtime."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from app.core.exceptions import AppException
from app.modules.modelops.schemas import ChatMessage
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from app.modules.rag.service import rag_service
from app.modules.workflows.nodes.base import WorkflowContext
from app.modules.workflows.nodes.llm_generate_node import LLMGenerateNodeHandler
from app.modules.workflows.nodes.rag_answer_node import RAGAnswerNodeHandler
from app.modules.workflows.schemas import WorkflowNodeSpec


def request(**updates):
    return AskRequest(question="Explain policy", collection_id="col_test", tenant_id="tenant_other",
                      workspace_id="workspace_other", preferred_model_name="configured-chat",
                      preferred_provider_id="configured-provider", **updates)


@pytest.mark.asyncio
async def test_rag_transmits_tenant_and_delegates_fallback_once():
    req = request(fallback_model="configured-fallback")
    with patch("app.modules.rag.service.modelops_service.generate", AsyncMock(
            return_value=SimpleNamespace(content="grounded answer"))) as generate:
        answer = await rag_service._generate_answer_with_fallback(
            AsyncMock(), req, [ChatMessage(role="user", content="question")], 0.2, None, [])
    assert answer == "grounded answer"
    llm_req = generate.call_args.args[1]
    assert llm_req.tenant_id == "tenant_other"
    assert llm_req.preferred_provider_id == "configured-provider"
    assert llm_req.preferred_model_name == "configured-chat"
    assert llm_req.fallback_model_name == "configured-fallback"
    generate.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["ALL_PROVIDERS_UNAVAILABLE", "QUOTA_EXCEEDED"])
async def test_modelops_failure_is_never_a_successful_extract(code):
    outage = AppException("unavailable", code=code, status_code=503)
    with (patch("app.modules.rag.service.modelops_service.generate", AsyncMock(side_effect=outage)) as generate,
          pytest.raises(AppException) as error):
        await rag_service._generate_answer_with_fallback(
            AsyncMock(), request(fallback_model="fallback"), [ChatMessage(role="user", content="question")],
            0.2, "| evidenced facts |", [FusionCandidate("c", "b", "source text", 0.03)])
    assert error.value is outage
    generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_llm_node_inherits_provider_and_preserves_modelops_error():
    policy = SimpleNamespace(primary_model="custom-model", fallback_model=None,
                             preferred_provider_id="profile-provider", temperature=0.1, max_tokens=1500)
    profile = SimpleNamespace(model_policy=policy, system_prompt="system", assistant_code="test")
    context = WorkflowContext("test", "tenant_other", None, {"message": "hello"},
                              assistant_profile=profile, db=AsyncMock())
    node = WorkflowNodeSpec(id="llm", type="llm.generate")
    with patch("app.modules.workflows.nodes.llm_generate_node.modelops_service.generate",
               AsyncMock(return_value=SimpleNamespace(content="answer", provider="profile-provider", total_tokens=1))) as generate:
        await LLMGenerateNodeHandler().execute(node, context)
    assert generate.call_args.args[1].preferred_provider_id == "profile-provider"
    outage = AppException("unavailable", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503)
    with (patch("app.modules.workflows.nodes.llm_generate_node.modelops_service.generate", AsyncMock(side_effect=outage)),
          pytest.raises(AppException) as error):
        await LLMGenerateNodeHandler().execute(node, context)
    assert error.value is outage


@pytest.mark.asyncio
@pytest.mark.parametrize("handler,node_type", [(LLMGenerateNodeHandler(), "llm.generate"),
                                               (RAGAnswerNodeHandler(), "rag.answer")])
async def test_missing_database_never_returns_fake_success(handler, node_type):
    context = WorkflowContext("test", "tenant_other", None, {"message": "hello"})
    with pytest.raises(AppException) as error:
        await handler.execute(WorkflowNodeSpec(id="node", type=node_type, config={"collection_id": "col_test"}), context)
    assert error.value.code == "WORKFLOW_DATABASE_REQUIRED"


@pytest.mark.asyncio
async def test_cache_version_changes_with_prompt_provider_and_policy():
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="col_test", binding_revisions={})
    versions = []
    with (patch.object(hybrid_retriever, "resolve_retrieval_snapshot", AsyncMock(return_value=snapshot)),
          patch("app.modules.rag.service.semantic_cache.get", AsyncMock(return_value={
              "status": "answered", "answer": "cached", "citations": []})) as cache):
        for req in [request(), request(system_prompt="new persona"),
                    request(reranker_policy={"enabled": False}), request(assistant_revision="revision2")]:
            await rag_service.ask(AsyncMock(), req)
            versions.append(cache.call_args.kwargs.get("policy_version"))
    assert None not in versions
    assert len(set(versions)) == 4


@pytest.mark.asyncio
async def test_neighbor_sql_supports_binding_only_with_pinned_scope():
    chunk = FusionCandidate("c", "binding", "text", 0.03, metadata={"chunk_index": 2},
                            binding_id="binding", index_revision_id="revision")
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="col_test",
                                 binding_revisions={"binding": "revision"},
                                 tenant_id="tenant_other", workspace_id="workspace_other")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [SimpleNamespace(id="neighbor", content="context")]
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    expanded = await hybrid_retriever.expand_with_neighbors(db, [chunk], "col_test", snapshot=snapshot)
    sql = str(db.execute.call_args.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert expanded == {"c": ["context"]}
    assert "JOIN knowledge_documents" not in sql
    assert "knowledge_chunks.binding_id = 'binding'" in sql
    assert "knowledge_chunks.index_revision_id = 'revision'" in sql
    assert "workspace_other" in sql and "tenant_other" in sql


@pytest.mark.asyncio
async def test_rag_router_uses_actor_not_body_scope():
    from app.modules.auth.schemas import AuthActor
    from app.modules.rag.router import ask_question
    from app.modules.rag.schemas import AskResponse

    actor = AuthActor(username="test", tenant_id="trusted_tenant", workspace_id="trusted_workspace")
    with patch.object(rag_service, "ask", AsyncMock(return_value=AskResponse(status="insufficient_context", answer="empty"))) as ask:
        await ask_question(request(), AsyncMock(), actor)
    scoped_request = ask.call_args.args[1]
    assert scoped_request.tenant_id == actor.tenant_id
    assert scoped_request.workspace_id == actor.workspace_id


@pytest.mark.asyncio
async def test_public_assistant_scope_comes_from_collection_and_rejects_cross_tenant():
    from app.modules.assistants.runtime import resolve_runtime_scope

    assistant = SimpleNamespace(collection_id="collection", tenant_id="tenant_owner")
    db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(tenant_id="tenant_owner", workspace_id="workspace_owner")))
    assert await resolve_runtime_scope(db, assistant) == ("tenant_owner", "workspace_owner")
    db.get.return_value.tenant_id = "tenant_attacker"
    with pytest.raises(AppException) as error:
        await resolve_runtime_scope(db, assistant)
    assert error.value.code == "ASSISTANT_SCOPE_MISMATCH"


@pytest.mark.asyncio
async def test_dag_failure_keeps_code_and_failed_node_trace():
    from app.modules.workflows.engine import dag_engine
    from app.modules.workflows.schemas import WorkflowDagSpec

    context = WorkflowContext("wf", "tenant_other", None, {"message": "hi"}, db=AsyncMock())
    spec = WorkflowDagSpec(entry_node_id="llm", nodes=[WorkflowNodeSpec(id="llm", type="llm.generate")])
    outage = AppException("provider unavailable", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503)
    with patch("app.modules.workflows.nodes.llm_generate_node.modelops_service.generate", AsyncMock(side_effect=outage)):
        result = await dag_engine.execute(spec, context)
    assert result.status == "failed"
    assert result.error_code == "ALL_PROVIDERS_UNAVAILABLE"
    assert context.node_traces[-1].status == "failed"
    assert context.node_traces[-1].output_data["error_code"] == result.error_code


def test_published_specialist_facts_share_scope_and_revision_filter():
    from app.modules.tools.consulting_dispatcher import published_fact_query

    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="col_test",
                                 binding_revisions={"binding": "published_revision"},
                                 tenant_id="tenant_other", workspace_id="workspace_other")
    sql = str(published_fact_query("col_test", snapshot).compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    for expected in ["tenant_other", "workspace_other", "published_revision", "knowledge_bindings.status = 'active'"]:
        assert expected in sql


def test_vllm_chat_provider_accepts_arbitrary_model_names():
    from app.modules.modelops.services.inference_service import (
        VALID_CHAT_PROVIDER_TYPES,
        _is_model_compatible_with_provider,
    )

    assert "vllm" in VALID_CHAT_PROVIDER_TYPES
    assert _is_model_compatible_with_provider({"provider_type": "vllm"}, "my-chat-model")
    assert _is_model_compatible_with_provider({"provider_type": "vllm"}, "Qwen/future-chat")


@pytest.mark.asyncio
async def test_failed_rag_ask_does_not_cache_a_success():
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="col_test", binding_revisions={})
    outage = AppException("outage", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503)
    with (patch.object(hybrid_retriever, "resolve_retrieval_snapshot", AsyncMock(return_value=snapshot)),
          patch.object(hybrid_retriever, "retrieve", AsyncMock(return_value=[FusionCandidate("c", "b", "source text", 0.03)])),
          patch.object(hybrid_retriever, "expand_with_neighbors", AsyncMock(return_value={})),
          patch("app.modules.rag.service.fact_layer.lookup_facts", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.semantic_cache.get", AsyncMock(return_value=None)),
          patch("app.modules.rag.service.semantic_cache.set", AsyncMock()) as cache_set,
          patch("app.modules.rag.service.modelops_service.generate", AsyncMock(side_effect=outage)),
          pytest.raises(AppException)):
        await rag_service.ask(AsyncMock(), request())
    cache_set.assert_not_awaited()


@pytest.mark.asyncio
async def test_lexical_search_matches_source_snapshot_metadata():
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.all.return_value = []
    db = SimpleNamespace(execute=AsyncMock(return_value=result), get=AsyncMock(return_value=SimpleNamespace(collection_metadata={})))
    snapshot = RetrievalSnapshot(snapshot_id="s", collection_id="col_test", binding_revisions={"b": "r"})
    await hybrid_retriever.search_sparse_fts(db, "col_test", "2705", snapshot=snapshot,
                                            tenant_id="tenant_other", workspace_id="workspace_other")
    sql = str(db.execute.call_args_list[0].args[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "document_title" in sql and "document_number" in sql
    assert "tenant_other" in sql and "workspace_other" in sql


def test_policy_fingerprint_changes_with_provider_and_limits():
    base = request()
    for update in [{"preferred_provider_id": "other-provider"}, {"max_tokens": 3000},
                   {"runtime_policy": {"guardrails": {"require_grounded_answer": True}}}]:
        assert base.policy_fingerprint() != base.model_copy(update=update).policy_fingerprint()
