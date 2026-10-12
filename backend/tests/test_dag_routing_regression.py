"""Regression tests for unequal branches and isolated wired node data."""

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.rag.schemas import AskResponse, RetrievalSnapshot
from app.modules.workflows.engine import dag_engine
from app.modules.workflows.nodes.base import BaseNodeHandler, NodeExecutionResult, WorkflowContext
from app.modules.workflows.nodes.citation_guard_node import CitationGuardNodeHandler
from app.modules.workflows.nodes.llm_generate_node import LLMGenerateNodeHandler
from app.modules.workflows.nodes.output_chat_node import OutputChatNodeHandler
from app.modules.workflows.nodes.rag_answer_node import RAGAnswerNodeHandler
from app.modules.workflows.registry import node_registry
from app.modules.workflows.schemas import WorkflowDagSpec, WorkflowEdgeSpec, WorkflowNodeSpec


class Probe(BaseNodeHandler):
    async def execute(self, node_spec, context):
        context.outputs.setdefault("order", []).append(node_spec.id)
        return NodeExecutionResult(
            node_id=node_spec.id,
            output={"value": node_spec.id},
            selected_port=node_spec.config.get("port"),
        )


def context():
    return WorkflowContext(workflow_id="test", tenant_id="test", conversation_id=None, inputs={})


@pytest.mark.asyncio
async def test_unequal_branches_wait_for_deep_predecessor(monkeypatch):
    monkeypatch.setitem(node_registry._handlers, "test.probe", Probe())
    ids = ["root", "a_short", "z_long", "zz_tail", "b_join", "out"]
    edges = [
        ("root", "a_short"),
        ("root", "z_long"),
        ("a_short", "b_join"),
        ("z_long", "zz_tail"),
        ("zz_tail", "b_join"),
        ("b_join", "out"),
    ]
    spec = WorkflowDagSpec(
        entry_node_id="root",
        nodes=[WorkflowNodeSpec(id=i, type="test.probe") for i in ids],
        edges=[WorkflowEdgeSpec(source=a, target=b) for a, b in edges],
    )
    ctx = context()
    result = await dag_engine.execute(spec, ctx)
    assert result.status == "completed"
    assert ctx.outputs["order"].index("zz_tail") < ctx.outputs["order"].index("b_join")


@pytest.mark.asyncio
async def test_output_uses_wired_answer_not_last_shared_answer():
    ctx = context()
    ctx.node_data = {"rag_answer": "wrong", "citations": [{"title": "wrong"}]}
    ctx.node_inputs["out"] = {"input": {"answer": "correct", "citations": [], "status": "answered"}}
    result = await OutputChatNodeHandler().execute(
        WorkflowNodeSpec(id="out", type="output.chat"), ctx
    )
    assert result.output["answer"] == "correct"
    assert result.output["citations"] == []


@pytest.mark.asyncio
async def test_llm_uses_wired_message():
    ctx = context()
    ctx.db = object()
    ctx.node_data["user_message"] = "wrong"
    ctx.node_inputs["llm"] = {"message": "correct"}
    response = type("Response", (), {"content": "ok", "provider": "test", "total_tokens": 1})()
    with patch(
        "app.modules.workflows.nodes.llm_generate_node.modelops_service.generate",
        AsyncMock(return_value=response),
    ) as generate:
        await LLMGenerateNodeHandler().execute(WorkflowNodeSpec(id="llm", type="llm.generate"), ctx)
        assert generate.call_args.args[1].messages[-1].content == "correct"


@pytest.mark.asyncio
async def test_missing_wired_port_fails_without_shared_fallback(monkeypatch):
    monkeypatch.setitem(node_registry._handlers, "test.probe", Probe())
    spec = WorkflowDagSpec(
        entry_node_id="root",
        nodes=[
            WorkflowNodeSpec(id="root", type="test.probe"),
            WorkflowNodeSpec(id="out", type="output.chat"),
        ],
        edges=[
            WorkflowEdgeSpec(
                source="root", target="out", source_port="missing", target_port="answer"
            )
        ],
    )
    ctx = context()
    ctx.node_data["rag_answer"] = "stale"
    result = await dag_engine.execute(spec, ctx)
    assert result.status == "failed"
    assert "answer" not in ctx.outputs
    assert "missing" in result.error_message


@pytest.mark.asyncio
async def test_selected_branch_skips_deep_unselected_path(monkeypatch):
    monkeypatch.setitem(node_registry._handlers, "test.probe", Probe())
    nodes = [
        WorkflowNodeSpec(id=i, type="test.probe", config={"port": "value"} if i == "route" else {})
        for i in ("route", "short", "long", "tail", "join")
    ]
    edges = [
        WorkflowEdgeSpec(source="route", target="short", source_port="value"),
        WorkflowEdgeSpec(source="route", target="long", source_port="unused"),
        WorkflowEdgeSpec(source="short", target="join"),
        WorkflowEdgeSpec(source="long", target="tail"),
        WorkflowEdgeSpec(source="tail", target="join"),
    ]
    ctx = context()
    result = await dag_engine.execute(
        WorkflowDagSpec(entry_node_id="route", nodes=nodes, edges=edges), ctx
    )
    assert result.status == "completed"
    assert ctx.outputs["order"] == ["route", "short", "join"]


@pytest.mark.asyncio
async def test_branch_port_to_same_target_uses_only_selected_value(monkeypatch):
    monkeypatch.setitem(node_registry._handlers, "test.probe", Probe())
    spec = WorkflowDagSpec(
        entry_node_id="route",
        nodes=[
            WorkflowNodeSpec(id="route", type="test.probe", config={"port": "value"}),
            WorkflowNodeSpec(id="out", type="output.chat"),
        ],
        edges=[
            WorkflowEdgeSpec(
                source="route", target="out", source_port="value", target_port="answer"
            ),
            WorkflowEdgeSpec(
                source="route", target="out", source_port="unused", target_port="answer"
            ),
        ],
    )
    result = await dag_engine.execute(spec, context())
    assert result.status == "completed"
    assert result.outputs["answer"] == "route"


@pytest.mark.asyncio
async def test_resume_preserves_other_pending_branch(monkeypatch):
    monkeypatch.setitem(node_registry._handlers, "test.probe", Probe())
    nodes = [
        WorkflowNodeSpec(id=i, type="human.approval" if i == "a_approval" else "test.probe")
        for i in ("root", "a_approval", "z_long", "zz_tail", "b_join")
    ]
    edges = [
        ("root", "a_approval"),
        ("root", "z_long"),
        ("a_approval", "b_join"),
        ("z_long", "zz_tail"),
        ("zz_tail", "b_join"),
    ]
    spec = WorkflowDagSpec(
        entry_node_id="root",
        nodes=nodes,
        edges=[WorkflowEdgeSpec(source=a, target=b) for a, b in edges],
    )
    ctx = context()
    paused = await dag_engine.execute(spec, ctx)
    assert paused.status == "paused_for_approval"
    ctx.inputs["is_approved"] = True
    resumed = await dag_engine.execute(
        spec, ctx, start_node_id="a_approval", completed_node_ids={"root"}
    )
    assert resumed.status == "completed"
    assert ctx.outputs["order"].index("zz_tail") < ctx.outputs["order"].index("b_join")


@pytest.mark.asyncio
async def test_rag_reads_wired_question():
    ctx = context()
    ctx.db = object()
    ctx.node_data["normalized_query"] = "wrong"
    ctx.node_inputs["rag"] = {"question": "correct"}
    with (
        patch("app.modules.workflows.nodes.rag_answer_node.hybrid_retriever.resolve_retrieval_snapshot",
              AsyncMock(return_value=RetrievalSnapshot(snapshot_id="s", collection_id="test"))),
        patch(
            "app.modules.tools.consulting_dispatcher.consulting_dispatcher.dispatch",
            AsyncMock(return_value={}),
        ),
        patch(
            "app.modules.workflows.nodes.rag_answer_node.rag_service.ask",
            AsyncMock(return_value=AskResponse(answer="ok", status="answered", citations=[])),
        ) as ask,
    ):
        await RAGAnswerNodeHandler().execute(
            WorkflowNodeSpec(id="rag", type="rag.answer", config={"collection_id": "test"}), ctx
        )
        assert ask.call_args.args[1].question == "correct"


@pytest.mark.asyncio
async def test_guard_does_not_use_other_branch_evidence():
    ctx = context()
    ctx.node_data.update(
        {
            "rag_answer": "21.341.000",
            "contexts": ["21.341.000"],
            "citations": [{"quote": "21.341.000"}],
        }
    )
    ctx.node_inputs["guard"] = {
        "input": {"answer": "42.000", "citations": [], "status": "answered"}
    }
    result = await CitationGuardNodeHandler().execute(
        WorkflowNodeSpec(id="guard", type="guard.citation"), ctx
    )
    assert result.selected_port == "ungrounded"


@pytest.mark.asyncio
async def test_invalid_text_input_does_not_fall_back():
    ctx = context()
    ctx.node_data["user_message"] = "stale"
    ctx.node_inputs["llm"] = {"message": None}
    with pytest.raises(Exception, match="không hợp lệ"):
        await LLMGenerateNodeHandler().execute(WorkflowNodeSpec(id="llm", type="llm.generate"), ctx)


@pytest.mark.asyncio
async def test_duplicate_explicit_target_port_fails(monkeypatch):
    monkeypatch.setitem(node_registry._handlers, "test.probe", Probe())
    spec = WorkflowDagSpec(
        entry_node_id="root",
        nodes=[
            WorkflowNodeSpec(id=i, type="test.probe") for i in ("root", "left", "right", "join")
        ],
        edges=[
            WorkflowEdgeSpec(source="root", target="left"),
            WorkflowEdgeSpec(source="root", target="right"),
            WorkflowEdgeSpec(source="left", target="join", source_port="value", target_port="text"),
            WorkflowEdgeSpec(
                source="right", target="join", source_port="value", target_port="text"
            ),
        ],
    )
    result = await dag_engine.execute(spec, context())
    assert result.status == "failed"
    assert "nhiều dữ liệu" in result.error_message


@pytest.mark.asyncio
async def test_scalar_answer_keeps_evidence_from_its_source(monkeypatch):
    class Evidence(Probe):
        async def execute(self, node_spec, ctx):
            return NodeExecutionResult(
                node_id=node_spec.id,
                output={
                    "answer": "correct",
                    "citations": [{"quote": "correct"}],
                    "contexts": ["correct"],
                    "status": "answered",
                },
            )

    monkeypatch.setitem(node_registry._handlers, "test.evidence", Evidence())
    spec = WorkflowDagSpec(
        entry_node_id="rag",
        nodes=[
            WorkflowNodeSpec(id="rag", type="test.evidence"),
            WorkflowNodeSpec(id="out", type="output.chat"),
        ],
        edges=[
            WorkflowEdgeSpec(
                source="rag", target="out", source_port="answer", target_port="response"
            )
        ],
    )
    ctx = context()
    ctx.outputs["artifacts"] = ["wrong"]
    ctx.node_data["citations"] = [{"quote": "wrong"}]
    result = await dag_engine.execute(spec, ctx)
    assert result.status == "completed"
    assert result.outputs["citations"] == [{"quote": "correct"}]
    assert result.outputs["contexts"] == ["correct"]
    assert result.outputs["artifacts"] == []
